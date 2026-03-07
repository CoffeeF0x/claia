"""
Simple agent plugin for CLAIA.
A simple agent that directly calls a model for inference.
"""

# External dependencies
import logging
import pluggy
from typing import Type

# Internal dependencies
from ..lib import BaseAgent, Process
from ..lib.enums.conversation import MessageRole
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

  Consumes the token generator from registry.run(), emitting "token"
  callbacks on the process for each chunk. On completion emits
  "complete"; on failure emits "error".
  """

  @classmethod
  def process_request(cls, process, registry=None, **kwargs) -> object:
    """Process a model inference request by streaming tokens from the registry."""
    try:
      model_id = process.parameters["model_id"]
      full_response = ""

      for token in registry.run(model_id, process.conversation, streaming=True, **kwargs):
        full_response += token
        process.emit("token", token)

      process.conversation.add_message(MessageRole.ASSISTANT, full_response)
      process.mark_completed(full_response)

    except Exception as e:
      logging.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
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
      required_args=None
    )
