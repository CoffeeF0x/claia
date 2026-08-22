"""
Simple agent for CLAIA.

Owns the generate loop and the per-turn ``TagParser``. As deployment
chunks arrive the agent feeds them through the parser, appends utility
messages for any closed tags, and dispatches ``TagType.TOOL`` events
through ``Registry.execute_tool``. Tool results become a user-turn
``[TOOL_RESULT]`` message; the agent then generates again until a
turn has no tool call.
"""

import json
import logging
from typing import Iterable, List, Optional, Tuple

from .base import BaseAgent
from .system import compose_system_prompt, format_tool_result
from ..decorators import agent
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
from ...core.results import Result
from ...core.tools.protocols.simple.payload import decode_payload


logger = logging.getLogger(__name__)


########################################################################
#                          SIMPLE AGENT CLASS                          #
########################################################################
@agent
@agent.name("simple")
@agent.title("Simple Agent")
@agent.description("A simple agent that directly calls a model for inference")
class SimpleAgent(BaseAgent):
  """
  A simple agent that directly calls a model for inference.

  Streams ``BaseChunk`` items from ``registry.run`` and forwards
  visible text through ``TaskEvent.TOKEN``. Each text chunk is
  also fed to a ``TagParser`` configured from the model definition's
  ``tag_overrides``; closed tags become utility messages on the
  conversation, and tool tags are dispatched through
  ``registry.execute_tool``. Results from a turn are posted as one
  ``MessageRole.USER`` message of ``[TOOL_RESULT]`` blocks, then
  the agent generates again. The loop stops when a turn has no
  tool call, or after ``MAX_TOOL_ROUNDS``.

  The generate-time ``system`` string is composed once per task:
  tool-calling instructions (from ``registry.list_tools()`` and the
  model's tag specs) prepended to the caller-supplied persona, or a
  default helpful-assistant prompt when none is given.

  Non-text chunks (image / audio) follow the artifact attachment path.
  """

  MAX_TOOL_ROUNDS = 8

  @classmethod
  def execute(cls, task, registry, **kwargs) -> object:
    """Stream model turns, dispatch tools, and generate until done.

    Each generate mutates the conversation through the streaming
    helpers (one ``STREAM_START`` / ``STREAM_END`` per turn). Closed
    tags become utilities; tool results become a user message and
    trigger another generate. Per-token appends are silent;
    consumers wanting real-time progress listen on the task's
    ``TaskEvent.TOKEN`` callback.
    """
    conversation = task.conversation
    streaming_message = None

    try:
      model_id = task.parameters["model_id"]
      system = kwargs.pop("system", None)
      if system is None:
        system = task.parameters.get("system")

      tag_specs = cls._resolve_tag_specs(registry, model_id)
      system = compose_system_prompt(
        system,
        tools=registry.list_tools(),
        tag_specs=tag_specs,
      )

      last_response = ""
      for _round in range(cls.MAX_TOOL_ROUNDS):
        streaming_message = conversation.start_streaming_message(MessageRole.ASSISTANT)
        parser = TagParser(tag_specs)
        cancelled = False
        round_text = ""
        tool_results: List[Tuple[str, str]] = []

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

        # Flush is inside the success path so cancellation does not
        # fire tool dispatches for an unclosed tail.
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

        last_response = round_text
        cls._post_tool_results(task, conversation, tool_results)

        if cancelled:
          task.mark_cancelled(last_response)
          return task
        if not tool_results:
          task.mark_completed(last_response)
          return task

      task.mark_completed(last_response)

    except Exception as e:
      logging.exception(f"Error in SimpleAgent for {task.id}: {str(e)}")
      if streaming_message is not None:
        try:
          conversation.end_streaming_message(streaming_message.message_id, error=str(e))
        except Exception:
          logging.exception(
            f"Failed to mark streaming message ended after error: {streaming_message.message_id}"
          )
      task.mark_failed(str(e))

    return task

  # ------------------------------------------------------------------
  # Parser integration
  # ------------------------------------------------------------------
  @classmethod
  def _resolve_tag_specs(cls, registry, model_id: str):
    """Resolve the ``TagSpec`` list active for ``model_id``.

    Falls back to ``DEFAULT_TAGS`` (via ``resolve_tag_specs(None)``)
    when the registry has no definition for ``model_id``.
    """
    definitions = registry.get_supported_models()
    model_def = None
    if isinstance(definitions, dict) and model_id in definitions:
      model_def = definitions[model_id]
    return resolve_tag_specs(model_def)

  @classmethod
  def _post_tool_results(cls, task, conversation, results: List[Tuple[str, str]]) -> None:
    """Persist one user message for every tool result from this turn.

    All results from the same assistant stream share a single user
    message so the next generate stays user/assistant/user rather
    than a run of same-role turns.
    """
    if not results:
      return
    text = "\n\n".join(
      format_tool_result(name, body) for name, body in results
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
    """Drain a parser event iterator, dispatching tools as we go.

    Returns ``(name, body)`` pairs for each tool dispatch (including
    typed errors). ``TextEvent`` items are ignored: their text was
    already emitted as part of the originating chunk.
    """
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
    """Append a utility message for ``ev`` and dispatch tool calls.

    Always records the tag as a utility so persistence and observers
    keep the structured span. For ``TagType.TOOL`` events the agent
    then dispatches through ``registry.execute_tool`` and returns
    ``(name, body)`` for the user-turn result. Thinking and other
    tags return ``None``.
    """
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
    """Dispatch a TOOL ``TagEvent`` through ``registry.execute_tool``.

    Pulls the target name from the tag's attributes first, then from
    the JSON payload's envelope ``name`` field. When both sources are
    silent the dispatch fails with a typed message rather than
    guessing. The pair is posted later as a user ``[TOOL_RESULT]``.
    """
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
    """Pull the dispatch name out of attributes or the JSON envelope."""
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
    """Stringify a ``Result`` for a ``[TOOL_RESULT]`` body."""
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
    """Convert an image byte chunk into an artifact attached to the message."""
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
      logging.exception(f"Failed to attach generated image artifact: {e}")

  @staticmethod
  def _attach_audio_chunk(task, message_id: str, chunk: BaseChunk) -> None:
    """Convert an audio byte chunk into an artifact attached to the message."""
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
      logging.exception(f"Failed to attach generated audio artifact: {e}")
