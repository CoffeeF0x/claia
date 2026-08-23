"""
Base agent class for CLAIA.

Shared utilities: system-prompt composition, one-turn streaming
(parse / tool dispatch / message bookkeeping). Concrete agents
implement ``step`` — one unit of work reported as an ``AgentStatus``.
The framework drives steps: the queue worker runs one step per
dispatch and re-enqueues tasks that report ``CONTINUE``; ``execute``
drives steps to completion synchronously for direct (queue-less) use.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from ...core.data.artifacts import ToolArtifact
from ...core.data.chunks import AudioChunk, BaseChunk, ImageChunk, TextChunk
from ...core.data.models import AudioArtifact, ImageArtifact
from ...core.enums.agent import AgentStatus
from ...core.enums.conversation import MessageRole
from ...core.enums.data import AudioFormat, ImageFormat
from ...core.enums.parser import TagType
from ...core.enums.task import TaskEvent, TaskStatus
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
  """Utilities for agents. ``step`` is implemented by each agent."""

  DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
  MAX_TOOL_ROUNDS = 8
  # Reserved key in task.parameters holding the chat-loop round counter.
  ROUND_PARAMETER = "round"

  @classmethod
  def run(cls, task: Task, registry, **kwargs) -> Task:
    """Run one step and apply its ``AgentStatus`` to the task.

    Called once per queue dispatch. The first step validates the task
    and fires the started transition; a ``CONTINUE`` step leaves the
    task ``PENDING`` so the queue can re-enqueue it.
    """
    try:
      if task.cancel_requested:
        task.mark_cancelled(task.result)
        return task

      if task.started_at is None:
        logger.info(f"Starting task {task.id} with agent {cls.__name__}")
        task.mark_started()  # Legacy transition: fires once per task.
        cls.validate_task(task, registry)
      else:
        task.status = TaskStatus.PROCESSING

      status = cls.step(task, registry=registry, **kwargs)
      cls._apply_agent_status(task, status)
    except Exception as e:
      logger.exception(f"Error running {task.id} with agent {cls.__name__}: {str(e)}")
      task.mark_failed(str(e))
    return task

  @classmethod
  def execute(cls, task: Task, registry, **kwargs) -> Task:
    """Direct path: drive ``run`` until the task is terminal, no queue."""
    while True:
      cls.run(task, registry=registry, **kwargs)
      if task.status is not TaskStatus.PENDING:
        return task

  @classmethod
  def step(cls, task: Task, registry, **kwargs) -> AgentStatus:
    """Implemented by each agent: one unit of work.

    Loop state belongs in ``task.parameters`` so it survives
    re-enqueues and stays externally visible. Set ``task.result`` /
    ``task.error`` before returning a terminal status; the framework
    owns the actual task state transition.
    """
    logger.error(f"step not implemented for {cls.__name__}")
    raise NotImplementedError(
      f"Agent implementation {cls.__name__} must override step"
    )

  @classmethod
  def _apply_agent_status(cls, task: Task, status: AgentStatus) -> None:
    """Convert a step's ``AgentStatus`` into the task state transition."""
    if status is AgentStatus.CONTINUE:
      task.status = TaskStatus.PENDING
    elif status is AgentStatus.COMPLETED:
      task.mark_completed(task.result)
    elif status is AgentStatus.CANCELLED:
      task.mark_cancelled(task.result)
    elif status is AgentStatus.FAILED:
      task.mark_failed(task.error or "Agent step failed")
    else:
      raise TypeError(
        f"{cls.__name__}.step must return an AgentStatus, got {status!r}"
      )

  @classmethod
  def chat_step(
    cls,
    task: Task,
    registry,
    *,
    system: Optional[str] = None,
    **kwargs,
  ) -> AgentStatus:
    """One tool-loop turn: stream, dispatch tools, advance the round.

    The shared chat-agent step. The calling agent picks the persona
    (``system``); the round counter lives in ``task.parameters``.
    """
    # Task-owned keys also arrive via kwargs when dispatched off the
    # queue (dispatch merges task.parameters into the call kwargs);
    # drop them so they never reach the model call.
    kwargs.pop("model_id", None)
    kwargs.pop(cls.ROUND_PARAMETER, None)

    model_id = task.parameters["model_id"]
    round_index = int(task.parameters.get(cls.ROUND_PARAMETER, 0))
    tag_specs = cls.resolve_tag_specs(registry, model_id)
    composed = cls.compose_system_prompt(
      system,
      tools=registry.list_tools(),
      tag_specs=tag_specs,
    )

    text, results, cancelled = cls.stream_turn(
      task,
      registry,
      model_id=model_id,
      system=composed,
      tag_specs=tag_specs,
      **kwargs,
    )
    task.parameters[cls.ROUND_PARAMETER] = round_index + 1
    task.result = text

    if cancelled:
      return AgentStatus.CANCELLED
    if not results or round_index + 1 >= cls.MAX_TOOL_ROUNDS:
      return AgentStatus.COMPLETED
    return AgentStatus.CONTINUE

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

    Returns ``(text, tool_results, cancelled)``. Tool results are
    attached as ``ToolArtifact``s on the parsed TOOL utilities. The
    caller decides whether to generate again.
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
          task=task,
        ))

      if not cancelled:
        tool_results.extend(cls._consume_parse_events(
          parser.flush(),
          registry=registry,
          conversation=conversation,
          streaming_message_id=streaming_message.message_id,
          tool_kwargs=kwargs,
          task=task,
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
      "Call one tool at a time. Tool results arrive as a [TOOL_RESULT] block",
      "on the following turn — not a new human request. Continue: call",
      "another tool the same way, or answer the user. Do not invent tools.",
      "",
      "Available tools:",
    ]
    for tool in tools:
      lines.extend(cls._format_tool(tool))
    return "\n".join(lines)

  @classmethod
  def format_tool_result(cls, name: str, body: str) -> str:
    """Default MANUAL-mode presentation of a tool result."""
    return ToolArtifact.format_result(name, body)

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
  def _consume_parse_events(
    cls,
    events: Iterable[ParseEvent],
    *,
    registry,
    conversation,
    streaming_message_id: str,
    tool_kwargs: dict,
    task=None,
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
          task=task,
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
    task=None,
  ) -> Optional[Tuple[str, str]]:
    utility = conversation.append_utility(
      tag_type=ev.tag_type,
      content=ev.content,
      source_message_id=streaming_message_id,
      start_index=ev.start_index,
      end_index=ev.end_index,
      attributes=dict(ev.attributes) if ev.attributes else None,
    )

    if ev.tag_type is not TagType.TOOL:
      return None

    result = cls._dispatch_tool_event(
      ev,
      registry=registry,
      conversation=conversation,
      tool_kwargs=tool_kwargs,
    )
    artifact = ToolArtifact.from_result(result[0], result[1])
    conversation.attach_artifact(utility.message_id, artifact)
    if task is not None:
      task.emit(TaskEvent.ARTIFACT, artifact, utility.message_id)
    return result

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
