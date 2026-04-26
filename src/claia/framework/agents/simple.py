"""
Simple agent plugin for CLAIA.
A simple agent that directly calls a model for inference.
"""

import logging
from typing import Optional, Type

from .base import BaseAgent
from claia.core.data.models import AudioArtifact, ImageArtifact
from claia.core.enums.conversation import MessageRole
from claia.core.modality import ChunkKind, GenerationChunk
from ..hooks import AgentInfo


########################################################################
#                          SIMPLE AGENT CLASS                          #
########################################################################
class SimpleAgent(BaseAgent):
  """
  A simple agent that directly calls a model for inference.

  Consumes the ``GenerationChunk`` generator from ``registry.run``,
  emitting ``"token"`` callbacks on the process for each text chunk
  and forwarding non-text chunks (e.g. progress updates, image bytes)
  via a ``"chunk"`` event for consumers that want the richer stream.
  On completion emits ``"complete"``; on failure emits ``"error"``.
  """

  @classmethod
  def process_request(cls, process, registry=None, **kwargs) -> object:
    """
    Process a model inference request by streaming tokens from the registry.

    The conversation is mutated through the dedicated streaming methods so
    that the conversation observer (if any) sees a single STREAM_START with
    an empty placeholder message before tokens flow, and a single STREAM_END
    once the response completes. Per-token appends are intentionally silent
    to avoid flooding observers; consumers that need real-time progress
    listen for the process's "token" callback instead.
    """
    conversation = process.conversation
    streaming_message = None

    try:
      model_id = process.parameters["model_id"]
      full_response = ""

      streaming_message = conversation.start_streaming_message(MessageRole.ASSISTANT)
      process.emit("stream_start", streaming_message.message_id)

      cancelled = False
      for chunk in registry.run(model_id, conversation, streaming=True, **kwargs):
        if process.cancel_requested:
          cancelled = True
          break
        if chunk.kind is not ChunkKind.TEXT:
          if chunk.kind is ChunkKind.IMAGE_BYTES:
            cls._attach_image_chunk(process, streaming_message.message_id, chunk)
          elif chunk.kind is ChunkKind.AUDIO_BYTES:
            cls._attach_audio_chunk(process, streaming_message.message_id, chunk)
          process.emit("chunk", chunk)
          continue
        token = chunk.data if isinstance(chunk.data, str) else str(chunk.data)
        full_response += token
        conversation.append_stream_chunk(streaming_message.message_id, token)
        process.emit("token", token)

      if cancelled:
        conversation.end_streaming_message(streaming_message.message_id, error="cancelled")
        process.emit("stream_end", streaming_message.message_id)
        process.emit("cancelled", full_response)
        process.mark_cancelled()
      else:
        conversation.end_streaming_message(streaming_message.message_id)
        process.emit("stream_end", streaming_message.message_id)
        process.mark_completed(full_response)

    except Exception as e:
      logging.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
      if streaming_message is not None:
        try:
          conversation.end_streaming_message(streaming_message.message_id, error=str(e))
          process.emit("stream_end", streaming_message.message_id)
        except Exception:
          logging.exception(
            f"Failed to mark streaming message ended after error: {streaming_message.message_id}"
          )
      process.mark_failed(str(e))

    return process

  @staticmethod
  def _attach_image_chunk(process, message_id: str, chunk: GenerationChunk) -> None:
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

      artifact = ImageArtifact.from_bytes(
        image_data=chunk.data,
        name=name,
        format=output_format,
        media_type=metadata.get("media_type", "image/png"),
        metadata=metadata,
      )
      process.conversation.attach_file(message_id, artifact.id)
      process.emit("artifact", artifact, message_id)
    except Exception as e:
      logging.exception(f"Failed to attach generated image artifact: {e}")

  @staticmethod
  def _attach_audio_chunk(process, message_id: str, chunk: GenerationChunk) -> None:
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

      artifact = AudioArtifact.from_bytes(
        audio_data=chunk.data,
        name=name,
        format=output_format,
        sample_rate=metadata.get("sample_rate"),
        media_type=metadata.get("media_type", "audio/wav"),
        metadata=metadata,
      )
      process.conversation.attach_file(message_id, artifact.id)
      process.emit("artifact", artifact, message_id)
    except Exception as e:
      logging.exception(f"Failed to attach generated audio artifact: {e}")


########################################################################
#                            PLUGIN HOOKS                              #
########################################################################
class SimpleAgentPlugin:
  """Plugin implementation for the simple agent.

  The framework wraps this plain class in an :class:`AgentRegistrar`
  before registering it with pluggy, so no ``@hookimpl`` decorators are
  needed here.
  """

  info = AgentInfo(
    name="simple",
    title="Simple Agent",
    description="A simple agent that directly calls a model for inference",
    agent_class=SimpleAgent,
  )

  def get_agent_class(self, agent_name: str) -> Optional[Type[BaseAgent]]:
    """Return the agent class for a given ``agent_name`` (or None)."""
    if agent_name.lower() == "simple":
      return SimpleAgent
    return None

  def get_agent_info(self) -> AgentInfo:
    """Return metadata describing the simple agent."""
    return type(self).info
