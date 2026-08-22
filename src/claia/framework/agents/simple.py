"""
Simple agent for CLAIA.

Owns the per-turn ``TagParser``. As deployment chunks arrive the agent
feeds them through the parser, appends utility messages for any closed
tags, and dispatches ``TagType.TOOL`` events through
``Registry.execute_tool`` inline — the result text is appended to the
streaming assistant message and emitted as a ``ProcessEvent.TOKEN`` so
terminal renderers see the call → response flow without a separate
post-stream pass.
"""

import json
import logging
from typing import Iterable, Optional

from .base import BaseAgent
from ..decorators import agent
from ...core.data.chunks import AudioChunk, BaseChunk, ImageChunk, TextChunk
from ...core.data.models import AudioArtifact, ImageArtifact
from ...core.enums.conversation import MessageRole
from ...core.enums.data import AudioFormat, ImageFormat
from ...core.enums.process import ProcessEvent
from ...core.parser import (
  ParseError,
  ParseEvent,
  TagEvent,
  TagParser,
  TagType,
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
  visible text through ``ProcessEvent.TOKEN``. Each text chunk is
  also fed to a ``TagParser`` configured from the model definition's
  ``tag_overrides``; closed tags become utility messages on the
  conversation, and tool tags are dispatched through
  ``registry.execute_tool``. Tool-result text is streamed back to
  the user via the same ``"token"`` channel and appended to the
  active assistant message so it shows up inline in the transcript.

  Non-text chunks (image / audio) follow the artifact attachment path.
  """

  @classmethod
  def process_request(cls, process, registry, **kwargs) -> object:
    """Stream a model turn, parse tags inline, and dispatch tool calls.

    The conversation is mutated through the streaming-message
    helpers so observers see one ``STREAM_START`` and one
    ``STREAM_END`` per turn, with utility messages for parsed
    tags interleaved between them. Per-token appends are silent;
    consumers wanting real-time progress listen on the process's
    ``ProcessEvent.TOKEN`` callback.
    """
    conversation = process.conversation
    streaming_message = None

    try:
      model_id = process.parameters["model_id"]
      full_response = ""

      streaming_message = conversation.start_streaming_message(MessageRole.ASSISTANT)

      tag_specs = cls._resolve_tag_specs(registry, model_id)
      parser = TagParser(tag_specs)

      cancelled = False
      for chunk in registry.run(model_id, conversation, streaming=True, **kwargs):
        if process.cancel_requested:
          cancelled = True
          break

        if not isinstance(chunk, TextChunk):
          if isinstance(chunk, ImageChunk):
            cls._attach_image_chunk(process, streaming_message.message_id, chunk)
          elif isinstance(chunk, AudioChunk):
            cls._attach_audio_chunk(process, streaming_message.message_id, chunk)
          process.emit(ProcessEvent.CHUNK, chunk)
          continue

        token = chunk.data if isinstance(chunk.data, str) else str(chunk.data)
        full_response += token
        conversation.append_stream_chunk(streaming_message.message_id, token)
        process.emit(ProcessEvent.TOKEN, token)

        appended = cls._consume_parse_events(
          parser.feed(token),
          process=process,
          registry=registry,
          conversation=conversation,
          streaming_message_id=streaming_message.message_id,
          tool_kwargs=kwargs,
        )
        full_response += appended

      # End-of-stream: flush any pending events (tail text, unclosed
      # tags). The flush is intentionally inside the success path so
      # cancellation doesn't fire spurious tool dispatches.
      if not cancelled:
        appended = cls._consume_parse_events(
          parser.flush(),
          process=process,
          registry=registry,
          conversation=conversation,
          streaming_message_id=streaming_message.message_id,
          tool_kwargs=kwargs,
        )
        full_response += appended

      if cancelled:
        conversation.end_streaming_message(streaming_message.message_id, error="cancelled")
        process.mark_cancelled(full_response)
      else:
        conversation.end_streaming_message(streaming_message.message_id)
        process.mark_completed(full_response)

    except Exception as e:
      logging.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
      if streaming_message is not None:
        try:
          conversation.end_streaming_message(streaming_message.message_id, error=str(e))
        except Exception:
          logging.exception(
            f"Failed to mark streaming message ended after error: {streaming_message.message_id}"
          )
      process.mark_failed(str(e))

    return process

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
  def _consume_parse_events(
    cls,
    events: Iterable[ParseEvent],
    *,
    process,
    registry,
    conversation,
    streaming_message_id: str,
    tool_kwargs: dict,
  ) -> str:
    """Drain a parser event iterator, dispatching tools as we go.

    Returns the concatenation of any text appended to the streaming
    message as a side effect of dispatch (currently just tool result
    text). ``TextEvent`` items are intentionally ignored: their text
    was already emitted as part of the originating chunk.
    """
    appended = ""
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
        appended += cls._handle_tag_event(
          ev,
          process=process,
          registry=registry,
          conversation=conversation,
          streaming_message_id=streaming_message_id,
          tool_kwargs=tool_kwargs,
        )
    return appended

  @classmethod
  def _handle_tag_event(
    cls,
    ev: TagEvent,
    *,
    process,
    registry,
    conversation,
    streaming_message_id: str,
    tool_kwargs: dict,
  ) -> str:
    """Append a utility message for ``ev`` and dispatch tool calls.

    Always records the tag as a utility message so downstream
    consumers (persistence, observers, future replay tooling) get
    the structured span. For ``TagType.TOOL`` events the agent then
    resolves the qualified name and dispatches through
    ``registry.execute_tool``, streaming the result back to the
    active assistant message. Returns whatever extra text was
    appended to the streaming message so the agent can keep
    ``full_response`` accurate.
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
      return ""

    return cls._dispatch_tool_event(
      ev,
      process=process,
      registry=registry,
      conversation=conversation,
      streaming_message_id=streaming_message_id,
      tool_kwargs=tool_kwargs,
    )

  @classmethod
  def _dispatch_tool_event(
    cls,
    ev: TagEvent,
    *,
    process,
    registry,
    conversation,
    streaming_message_id: str,
    tool_kwargs: dict,
  ) -> str:
    """Dispatch a TOOL ``TagEvent`` through ``registry.execute_tool``.

    Pulls the target name from the tag's attributes first, then from
    the JSON payload's envelope ``name`` field. When both sources are
    silent the dispatch fails with a typed message rather than
    guessing. Result text is appended to the streaming message and
    emitted as a token so the user sees it inline.
    """
    name = cls._extract_tool_name(ev)
    if not name:
      return cls._emit_tool_output(
        f"[TOOL_ERROR] Tool call missing 'name' (tag attributes={ev.attributes})",
        process=process,
        conversation=conversation,
        streaming_message_id=streaming_message_id,
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
      return cls._emit_tool_output(
        f"[TOOL_ERROR] {exc}",
        process=process,
        conversation=conversation,
        streaming_message_id=streaming_message_id,
      )

    rendered = cls._render_result(result)
    return cls._emit_tool_output(
      rendered,
      process=process,
      conversation=conversation,
      streaming_message_id=streaming_message_id,
    )

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
    """Stringify a ``Result`` for inline streaming back to the user."""
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

  @staticmethod
  def _emit_tool_output(
    text: str,
    *,
    process,
    conversation,
    streaming_message_id: str,
  ) -> str:
    """Append ``text`` to the streaming message and emit it as a token.

    Splitting this out keeps the dispatch helpers free of streaming
    bookkeeping and makes the success / error paths share a single
    point of side effects.
    """
    if not text:
      return ""
    # The result is a separate streaming step from the model's own
    # output; prefix with a newline if the assistant didn't end on
    # one so the inline rendering reads naturally.
    prefix = ""
    try:
      latest = conversation.get_message(streaming_message_id)  # type: ignore[attr-defined]
      current = getattr(latest, "content", "") if latest is not None else ""
    except Exception:
      current = ""
    if current and not current.endswith("\n"):
      prefix = "\n"

    out = f"{prefix}{text}"
    conversation.append_stream_chunk(streaming_message_id, out)
    process.emit(ProcessEvent.TOKEN, out)
    return out

  # ------------------------------------------------------------------
  # Non-text chunk handling
  # ------------------------------------------------------------------
  @staticmethod
  def _attach_image_chunk(process, message_id: str, chunk: BaseChunk) -> None:
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
      process.conversation.attach_artifact(message_id, artifact)
      process.emit(ProcessEvent.ARTIFACT, artifact, message_id)
    except Exception as e:
      logging.exception(f"Failed to attach generated image artifact: {e}")

  @staticmethod
  def _attach_audio_chunk(process, message_id: str, chunk: BaseChunk) -> None:
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
      process.conversation.attach_artifact(message_id, artifact)
      process.emit(ProcessEvent.ARTIFACT, artifact, message_id)
    except Exception as e:
      logging.exception(f"Failed to attach generated audio artifact: {e}")
