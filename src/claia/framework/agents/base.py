"""
Base agent class for CLAIA.

Shared utilities: system-prompt composition, one-turn streaming
(parse / tool dispatch / message bookkeeping). Concrete agents
implement ``execute`` — they read the task and own the generate loop.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from ...core.data.chunks import AudioChunk, BaseChunk, ImageChunk, TextChunk
from ...core.data.models import AudioArtifact, ImageArtifact
from ...core.enums.conversation import MessageRole
from ...core.enums.data import AudioFormat, ImageFormat
from ...core.enums.parser import TagType
from ...core.enums.task import TaskEvent
from ...core.parser import (
  ParseError,
  ParseEvent,
  TagEvent,
  TagParser,
  TextEvent,
  resolve_tag_specs,
)
from ...core.plugins.base import ArgumentDefinition, ExtensionInfo, ToolReference
from ...core.parser.types import TagSpec
from ...core.results import Result
from ...core.tools.protocols.simple.payload import decode_payload
from ..task import Task


logger = logging.getLogger(__name__)

_INJECTABLE_ARGS = frozenset({
  "registry",
  "conversation",
  "settings",
  "command_specs",
  "current_mode",
  "kwargs",
})


########################################################################
#                          BASE AGENT CLASS                            #
########################################################################
class BaseAgent:
  """Utilities for agents. ``execute`` is implemented by each agent."""

  DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
  MAX_TOOL_ROUNDS = 8

  @classmethod
  def run(cls, task: Task, registry, **kwargs) -> object:
    """Mark the task started, validate, then call ``execute``."""
    logger.info(f"Starting task {task.id} with agent {cls.__name__}")
    task.mark_started()

    try:
      logger.debug(f"Validating requirements for task {task.id}")
      cls.validate_task(task, registry)

      logger.debug(f"Calling execute for {task.id} with agent {cls.__name__}")
      result = cls.execute(task, registry=registry, **kwargs)

      logger.info(f"Successfully completed task {task.id}")
      return result
    except Exception as e:
      logger.exception(f"Error running {task.id} with agent {cls.__name__}: {str(e)}")
      task.mark_failed(str(e))
      return task

  @classmethod
  def execute(cls, task: Task, registry, **kwargs) -> object:
    """Implemented by each agent: read the task, then call utilities."""
    logger.error(f"execute not implemented for {cls.__name__}")
    raise NotImplementedError(
      f"Agent implementation {cls.__name__} must override execute"
    )

  @classmethod
  def stream_turn(
    cls,
    task: Task,
    registry,
    *,
    model_id: str,
    system: str,
    tag_specs,
    **kwargs,
  ) -> Tuple[str, List[Tuple[str, str]], bool]:
    """One assistant stream: tokens, parse, tool dispatch.

    Returns ``(text, tool_results, cancelled)``. The caller posts
    results and decides whether to generate again.
    """
    conversation = task.conversation
    streaming_message = conversation.start_streaming_message(MessageRole.ASSISTANT)
    parser = TagParser(tag_specs)
    cancelled = False
    round_text = ""
    tool_results: List[Tuple[str, str]] = []

    try:
      for chunk in registry.run(
        model_id, conversation, streaming=True, system=system, **kwargs
      ):
        if task.cancel_requested:
          cancelled = True
          break

        if not isinstance(chunk, TextChunk):
          if isinstance(chunk, ImageChunk):
            cls._attach_image_chunk(task, streaming_message.message_id, chunk)
          elif isinstance(chunk, AudioChunk):
            cls._attach_audio_chunk(task, streaming_message.message_id, chunk)
          task.emit(TaskEvent.CHUNK, chunk)
          continue

        token = chunk.data if isinstance(chunk.data, str) else str(chunk.data)
        round_text += token
        conversation.append_stream_chunk(streaming_message.message_id, token)
        task.emit(TaskEvent.TOKEN, token)

        tool_results.extend(cls._consume_parse_events(
          parser.feed(token),
          registry=registry,
          conversation=conversation,
          streaming_message_id=streaming_message.message_id,
          tool_kwargs=kwargs,
        ))

      if not cancelled:
        tool_results.extend(cls._consume_parse_events(
          parser.flush(),
          registry=registry,
          conversation=conversation,
          streaming_message_id=streaming_message.message_id,
          tool_kwargs=kwargs,
        ))

      if cancelled:
        conversation.end_streaming_message(
          streaming_message.message_id, error="cancelled"
        )
      else:
        conversation.end_streaming_message(streaming_message.message_id)
    except Exception:
      try:
        conversation.end_streaming_message(
          streaming_message.message_id, error="stream failed"
        )
      except Exception:
        logger.exception(
          f"Failed to mark streaming message ended: {streaming_message.message_id}"
        )
      raise

    return round_text, tool_results, cancelled

  @classmethod
  def validate_task(cls, task: Task, registry) -> None:
    """Require a conversation, ``model_id``, and registry."""
    logger.debug(f"Validating task {task.id} requirements")

    if not task.conversation:
      logger.error(f"Task {task.id} missing conversation")
      raise ValueError(f"{cls.__name__} requires a conversation to work with")

    model_id = task.parameters.get("model_id")
    if not model_id:
      logger.error(f"Task {task.id} missing model_id in parameters")
      raise ValueError(f"{cls.__name__} requires a model_id in task parameters")

    if not registry:
      logger.error(f"Task {task.id} has no registry available")
      raise ValueError(f"{cls.__name__} requires a registry to be provided")

    logger.debug(f"Task {task.id} validated successfully with model {model_id}")

  @classmethod
  def get_description(cls) -> str:
    return cls.__doc__ or "No description available"

  # ------------------------------------------------------------------
  # System prompt
  # ------------------------------------------------------------------
  @classmethod
  def compose_system_prompt(
    cls,
    system: Optional[str] = None,
    *,
    tools: Optional[Iterable[ToolReference]] = None,
    tag_specs: Optional[Iterable[TagSpec]] = None,
  ) -> str:
    """Prepend MANUAL tool instructions to the persona, if any apply."""
    persona = (system or "").strip() or cls.DEFAULT_SYSTEM_PROMPT
    instructions = cls.render_tool_instructions(
      list(tools or []),
      list(tag_specs or []),
    )
    if not instructions:
      return persona
    return f"{instructions}\n\n{persona}"

  @classmethod
  def render_tool_instructions(
    cls,
    tools: List[ToolReference],
    tag_specs: List[TagSpec],
  ) -> str:
    """Return MANUAL-mode calling instructions, or ``""`` if none apply."""
    if not tools:
      return ""
    spec = cls._tool_spec(tag_specs)
    if spec is None:
      return ""

    lines = [
      "You can call tools by writing a tool-call tag in your reply.",
      "Use this exact format:",
      "",
      spec.open_token,
      '{"name": "<qualified tool name>", "parameters": { ... }}',
      spec.close_token,
      "",
      "Call one tool at a time. The next user message is the tool result",
      "in a [TOOL_RESULT] tag — not a new human request. Continue: call",
      "another tool the same way, or answer the user. Do not invent tools.",
      "",
      "Available tools:",
    ]
    for tool in tools:
      lines.extend(cls._format_tool(tool))
    return "\n".join(lines)

  @classmethod
  def format_tool_result(cls, name: str, body: str) -> str:
    """Render a tool result as a user-turn ``[TOOL_RESULT]`` block."""
    label = (name or "").strip() or "unknown"
    return f'[TOOL_RESULT name="{label}"]\n{body}\n[/TOOL_RESULT]'

  @staticmethod
  def _tool_spec(tag_specs: Iterable[TagSpec]) -> Optional[TagSpec]:
    for spec in tag_specs:
      if spec.tag_type is TagType.TOOL:
        return spec
    return None

  @classmethod
  def _format_tool(cls, tool: ToolReference) -> List[str]:
    name = tool.qualified_name
    description = (tool.description or "").strip()
    header = f"- {name}: {description}" if description else f"- {name}"
    lines = [header]
    lines.extend(cls._format_arguments(tool.parameter_schema))
    return lines

  @classmethod
  def _format_arguments(cls, schema: Any) -> List[str]:
    if not schema:
      return []

    if isinstance(schema, dict):
      if cls._looks_like_json_schema(schema):
        return cls._format_json_schema_args(schema)
      lines = []
      for name, spec in schema.items():
        if name in _INJECTABLE_ARGS:
          continue
        formatted = cls._format_one_argument(name, spec)
        if formatted:
          lines.append(formatted)
      return lines

    return []

  @staticmethod
  def _looks_like_json_schema(schema: Dict[str, Any]) -> bool:
    return "properties" in schema and isinstance(schema.get("properties"), dict)

  @classmethod
  def _format_json_schema_args(cls, schema: Dict[str, Any]) -> List[str]:
    required = set(schema.get("required") or [])
    lines = []
    for name, spec in (schema.get("properties") or {}).items():
      if name in _INJECTABLE_ARGS or not isinstance(spec, dict):
        continue
      type_name = spec.get("type") or "any"
      req = "required" if name in required else "optional"
      desc = (spec.get("description") or "").strip()
      line = f"  - {name} ({type_name}, {req})"
      if desc:
        line += f": {desc}"
      lines.append(line)
    return lines

  @staticmethod
  def _format_one_argument(name: str, spec: Any) -> Optional[str]:
    if isinstance(spec, ArgumentDefinition):
      req = "required" if spec.required else "optional"
      line = f"  - {name} ({spec.data_type}, {req})"
      if not spec.required and spec.default_value is not None:
        line += f", default={spec.default_value!r}"
      desc = (spec.description or "").strip()
      if desc:
        line += f": {desc}"
      return line

    if isinstance(spec, dict):
      type_name = spec.get("data_type") or spec.get("type") or "any"
      required = bool(spec.get("required", False))
      req = "required" if required else "optional"
      line = f"  - {name} ({type_name}, {req})"
      desc = (spec.get("description") or "").strip()
      if desc:
        line += f": {desc}"
      return line

    return None

  # ------------------------------------------------------------------
  # Parser / tools
  # ------------------------------------------------------------------
  @classmethod
  def resolve_tag_specs(cls, registry, model_id: str):
    """Resolve the ``TagSpec`` list active for ``model_id``."""
    definitions = registry.get_supported_models()
    model_def = None
    if isinstance(definitions, dict) and model_id in definitions:
      model_def = definitions[model_id]
    return resolve_tag_specs(model_def)

  @classmethod
  def _post_tool_results(cls, task, conversation, results: List[Tuple[str, str]]) -> None:
    """Persist one user message for every tool result from this turn."""
    if not results:
      return
    text = "\n\n".join(
      cls.format_tool_result(name, body) for name, body in results
    )
    conversation.add_message(MessageRole.USER, text)
    task.emit(TaskEvent.TOKEN, "\n" + text)

  @classmethod
  def _consume_parse_events(
    cls,
    events: Iterable[ParseEvent],
    *,
    registry,
    conversation,
    streaming_message_id: str,
    tool_kwargs: dict,
  ) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    for ev in events:
      if isinstance(ev, TextEvent):
        continue
      if isinstance(ev, ParseError):
        logger.debug(
          "Parser error %s at %d (expected=%r got=%r)",
          ev.reason, ev.position, ev.expected, ev.got,
        )
        continue
      if isinstance(ev, TagEvent):
        result = cls._handle_tag_event(
          ev,
          registry=registry,
          conversation=conversation,
          streaming_message_id=streaming_message_id,
          tool_kwargs=tool_kwargs,
        )
        if result is not None:
          results.append(result)
    return results

  @classmethod
  def _handle_tag_event(
    cls,
    ev: TagEvent,
    *,
    registry,
    conversation,
    streaming_message_id: str,
    tool_kwargs: dict,
  ) -> Optional[Tuple[str, str]]:
    conversation.append_utility(
      tag_type=ev.tag_type,
      content=ev.content,
      source_message_id=streaming_message_id,
      start_index=ev.start_index,
      end_index=ev.end_index,
      attributes=dict(ev.attributes) if ev.attributes else None,
    )

    if ev.tag_type is not TagType.TOOL:
      return None

    return cls._dispatch_tool_event(
      ev,
      registry=registry,
      conversation=conversation,
      tool_kwargs=tool_kwargs,
    )

  @classmethod
  def _dispatch_tool_event(
    cls,
    ev: TagEvent,
    *,
    registry,
    conversation,
    tool_kwargs: dict,
  ) -> Tuple[str, str]:
    name = cls._extract_tool_name(ev)
    if not name:
      return (
        "unknown",
        f"[TOOL_ERROR] Tool call missing 'name' (tag attributes={ev.attributes})",
      )

    qualified = registry.resolve_qualified_name(name) or name

    try:
      result = registry.execute_tool(
        qualified,
        ev.content,
        conversation,
        **tool_kwargs,
      )
    except Exception as exc:
      logger.exception("Error executing tool %r", qualified)
      return (qualified, f"[TOOL_ERROR] {exc}")

    return (qualified, cls._render_result(result))

  @staticmethod
  def _extract_tool_name(ev: TagEvent) -> Optional[str]:
    attr_name = ev.attributes.get("name") if ev.attributes else None
    if isinstance(attr_name, str) and attr_name.strip():
      return attr_name.strip()
    try:
      _params, name_hint = decode_payload(ev.content)
    except ValueError:
      return None
    if isinstance(name_hint, str) and name_hint.strip():
      return name_hint.strip()
    return None

  @staticmethod
  def _render_result(result: Result) -> str:
    if result is None:
      return ""
    if result.is_error():
      return f"[TOOL_ERROR] {result.get_message() or 'Unknown tool error'}"
    data = result.get_data()
    if data is None:
      return ""
    if isinstance(data, str):
      return data
    try:
      return json.dumps(data)
    except Exception:
      return str(data)

  # ------------------------------------------------------------------
  # Non-text chunk handling
  # ------------------------------------------------------------------
  @staticmethod
  def _attach_image_chunk(task, message_id: str, chunk: BaseChunk) -> None:
    try:
      metadata = dict(chunk.metadata or {})
      output_format = (metadata.get("format") or "PNG").upper()
      extension = {
        "JPEG": "jpg",
        "JPG": "jpg",
        "PNG": "png",
        "WEBP": "webp",
      }.get(output_format, output_format.lower())
      index = metadata.get("index", 0)
      name = metadata.get("name") or f"generated-image-{index + 1}.{extension}"
      try:
        image_fmt = (
          chunk.format
          if isinstance(chunk.format, ImageFormat)
          else ImageFormat(output_format.lower().replace("jpg", "jpeg"))
        )
      except ValueError:
        image_fmt = ImageFormat.PNG

      artifact = ImageArtifact.from_bytes(
        image_data=chunk.data,
        name=name,
        format=image_fmt,
        metadata=metadata,
      )
      task.conversation.attach_artifact(message_id, artifact)
      task.emit(TaskEvent.ARTIFACT, artifact, message_id)
    except Exception as e:
      logger.exception(f"Failed to attach generated image artifact: {e}")

  @staticmethod
  def _attach_audio_chunk(task, message_id: str, chunk: BaseChunk) -> None:
    try:
      metadata = dict(chunk.metadata or {})
      output_format = (metadata.get("format") or "WAV").upper()
      extension = {
        "WAV": "wav",
        "MP3": "mp3",
        "OPUS": "opus",
        "AAC": "aac",
        "FLAC": "flac",
      }.get(output_format, output_format.lower())
      index = metadata.get("index", 0)
      name = metadata.get("name") or f"generated-audio-{index + 1}.{extension}"
      audio_fmt = (
        chunk.format
        if isinstance(getattr(chunk, "format", None), AudioFormat)
        else AudioFormat.WAV
      )

      artifact = AudioArtifact.from_bytes(
        audio_data=chunk.data,
        name=name,
        format=audio_fmt,
        sample_rate=metadata.get("sample_rate"),
        metadata=metadata,
      )
      task.conversation.attach_artifact(message_id, artifact)
      task.emit(TaskEvent.ARTIFACT, artifact, message_id)
    except Exception as e:
      logger.exception(f"Failed to attach generated audio artifact: {e}")


########################################################################
#                              AGENT INFO                              #
########################################################################
@dataclass
class AgentInfo(ExtensionInfo):
  """Information about an agent implementation.

  Extends ``ExtensionInfo`` with the concrete ``agent_class`` used for
  dispatch. Entry-point agents leave ``agent_class`` unset; the manager
  fills it from the loaded class at discovery. Programmatic
  ``Registry.register`` supplies it directly.
  """
  agent_class: Optional[Type[BaseAgent]] = field(default=None)
