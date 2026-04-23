"""
Simple agent plugin for CLAIA.
A simple agent that directly calls a model for inference.
"""

# External dependencies
import logging
import pluggy
from typing import Type

# Internal dependencies
from .base import BaseAgent
from ..process import Process
from claia.core.enums.conversation import MessageRole
from claia.core.modality import ChunkKind
from ..hooks import AgentHooks, AgentInfo


########################################################################
#                            INITIALIZATION                            #
########################################################################
hookimpl = pluggy.HookimplMarker("claia_agents")


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
        # Non-text chunks (images, audio, progress, ...) are forwarded
        # to subscribers but do not contribute to the streamed text
        # body of the assistant message.
        if chunk.kind is not ChunkKind.TEXT:
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


########################################################################
#                            PLUGIN HOOKS                              #
########################################################################
class SimpleAgentPlugin:
  """Plugin implementation for the simple agent."""

  @hookimpl
  def get_agent_class(self, agent_name: str) -> Type[BaseAgent]:
    """Get the agent class for the simple agent."""
    if agent_name.lower() == "simple":
      return SimpleAgent
    return None

  @hookimpl
  def get_agent_info(self) -> AgentInfo:
    """Get information about the simple agent."""
    return AgentInfo(
      name="simple",
      title="Simple Agent",
      description="A simple agent that directly calls a model for inference",
      agent_class=SimpleAgent,
    )
