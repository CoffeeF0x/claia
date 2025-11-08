"""
Bob agent plugin for CLAIA.
Bob is a gruff, straightforward, no-nonsense assistant with a unique personality.
"""

# External dependencies
import logging
import pluggy
from typing import Type

# Internal dependencies
from claia.lib import BaseAgent, Process
from claia.hooks import AgentHooks, AgentInfo


########################################################################
#                              CONSTANTS                               #
########################################################################
# Bob Agent's system prompt
BOB_SYSTEM_PROMPT = """
You are Bob, a straightforward and no-nonsense assistant.
Bob speaks in the third person and keeps responses brief.
Bob doesn't use flowery language.
Bob is direct and sometimes sarcastic.
Bob always tries to be helpful despite his gruff demeanor.
"""


########################################################################
#                            INITIALIZATION                            #
########################################################################
hookimpl = pluggy.HookimplMarker("claia_agents")


########################################################################
#                            BOB AGENT CLASS                           #
########################################################################
class BobAgent(BaseAgent):
  """
  Bob is a gruff, straightforward, no-nonsense assistant with a unique personality.

  Bob applies his own system prompt to conversations for a distinctive interaction style.
  """

  @classmethod
  def process_request(cls, process, registry=None, **kwargs) -> object:
    """
    Process a request using Bob's unique style by applying his system prompt.

    Args:
        process: The process to execute
        registry: Registry instance to use for model operations
        **kwargs: Additional keyword arguments

    Returns:
        The updated process with results or error information
    """
    try:
      # Get the model ID from the validated parameters
      model_id = process.parameters["model_id"]

      # Set Bob's system prompt if it's different
      if process.conversation.prompt.get("system", "") != BOB_SYSTEM_PROMPT:
        process.conversation.change_prompt(BOB_SYSTEM_PROMPT)

      # Run the model with the conversation using the provided model registry
      result = registry.run(model_id, process.conversation, **kwargs)

      if result.is_error():
        raise ValueError(f"Bob ran into a problem: {result.get_message()}")

      process.mark_completed(result.data)

    except Exception as e:
      logging.exception(f"Bob encountered an error for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process


########################################################################
#                            PLUGIN HOOKS                              #
########################################################################
class BobAgentPlugin:
  """Plugin implementation for the Bob agent."""

  @hookimpl
  def get_agent_class(self, agent_name: str) -> Type[BaseAgent]:
    """Get the agent class for the Bob agent."""
    if agent_name.lower() == "bob":
      return BobAgent
    return None

  @hookimpl
  def get_agent_info(self) -> AgentInfo:
    """Get information about the Bob agent."""
    return AgentInfo(
      name="bob",
      description="A gruff, straightforward, no-nonsense assistant with a unique personality",
      agent_class=BobAgent
    )
