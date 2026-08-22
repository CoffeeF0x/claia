"""
CLI-specific agents for CLAIA.

This module contains custom agents that are registered programmatically
using the Registry.register() method, demonstrating how to create agents
without requiring an entry-point plugin.

Usage Example:
    # In the CLI, set the writer agent as active:
    :set active_agent writer

    # Then interact with the writer agent:
    Help me write a professional email to my team about the new project.

    # Or use it inline for a single request:
    :agent set writer
    Write a creative short story about a robot learning to paint.

The writer agent is automatically registered when the CLI starts up via
the register_cli_agents() function called in __main__.py.
"""

# External dependencies
import logging

# Internal dependencies
from ..framework.agents.base import BaseAgent
from ..core.data.chunks import TextChunk
from ..core.enums.conversation import MessageRole
from ..core.enums.task import TaskEvent


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                          WRITER AGENT CLASS                          #
########################################################################
# Writer-specific system prompt
WRITER_SYSTEM_PROMPT = """You are a professional writer and editor with expertise in various writing styles and formats.

Your capabilities include:
- Creative writing (stories, poetry, scripts)
- Technical writing (documentation, reports, manuals)
- Academic writing (essays, research papers, articles)
- Business writing (emails, proposals, presentations)
- Content writing (blogs, social media, marketing copy)

When helping with writing:
1. Understand the purpose and audience
2. Adapt your tone and style appropriately
3. Provide clear, well-structured content
4. Offer constructive feedback and suggestions
5. Help with grammar, clarity, and flow
6. Maintain consistency in voice and format

You prioritize clarity, engagement, and effective communication while respecting the user's unique voice and intentions."""


class WriterAgent(BaseAgent):
  """
  A specialized agent for writing tasks with enhanced literary capabilities.

  This agent passes a writer-focused system prompt on each generate
  call. Writing tasks include creative writing, technical
  documentation, business communications, and more.
  """

  @classmethod
  def execute(cls, task, registry, **kwargs) -> object:
    """Execute a writing request with specialized writing capabilities."""
    try:
      model_id = task.parameters.get("model_id")

      if not model_id:
        raise ValueError("No model_id provided in task parameters")

      kwargs.pop("system", None)
      logger.debug(f"Running model {model_id} for writing task {task.id}")
      full_response = ""

      for chunk in registry.run(
        model_id,
        task.conversation,
        streaming=True,
        system=WRITER_SYSTEM_PROMPT,
        **kwargs
      ):
        if not isinstance(chunk, TextChunk):
          task.emit(TaskEvent.CHUNK, chunk)
          continue
        token = chunk.data if isinstance(chunk.data, str) else str(chunk.data)
        full_response += token
        task.emit(TaskEvent.TOKEN, token)

      task.conversation.add_message(MessageRole.ASSISTANT, full_response)
      task.mark_completed(full_response)
      logger.info(f"Writer agent successfully completed task {task.id}")

    except Exception as e:
      logger.exception(f"Error in WriterAgent for {task.id}: {str(e)}")
      task.mark_failed(str(e))

    return task


########################################################################
#                        AGENT REGISTRATION                            #
########################################################################
def register_cli_agents(registry) -> None:
  """
  Register all CLI-specific agents with the provided registry.

  This demonstrates the programmatic agent registration approach using
  Registry.register() instead of an entry-point plugin.

  Args:
      registry: The Registry instance to register agents with
  """
  logger.info("Registering CLI-specific agents")

  # Register the Writer agent
  registry.register(
    agent_class=WriterAgent,
    name="writer",
    title="Writer Agent",
    description="A specialized agent for writing tasks with enhanced literary capabilities",
  )

  logger.debug("Successfully registered writer agent")

