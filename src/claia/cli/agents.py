"""
CLI-specific agents for CLAIA.

This module contains custom agents that are registered programmatically
using the Registry.register() method, demonstrating how to create agents
without requiring pluggy extensions.

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
from claia.lib import BaseAgent


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
  
  This agent applies a writer-focused system prompt to help with various
  writing tasks including creative writing, technical documentation,
  business communications, and more.
  """

  @classmethod
  def process_request(cls, process, registry=None, **kwargs) -> object:
    """
    Process a writing request with specialized writing capabilities.

    Args:
        process: The process to execute
        registry: Registry instance to use for model operations
        **kwargs: Additional keyword arguments

    Returns:
        The updated process with results or error information
    """
    try:
      # Get the model ID from the validated parameters
      model_id = process.parameters.get("model_id")
      
      if not model_id:
        raise ValueError("No model_id provided in process parameters")

      # Apply the writer's system prompt if different
      current_prompt = process.conversation.prompt.get("system", "")
      if current_prompt != WRITER_SYSTEM_PROMPT:
        logger.debug(f"Applying writer system prompt to process {process.id}")
        process.conversation.change_prompt(WRITER_SYSTEM_PROMPT)

      # Run the model with the conversation using the registry
      logger.debug(f"Running model {model_id} for writing task {process.id}")
      result = registry.run(model_id, process.conversation, **kwargs)

      if result.is_error():
        raise ValueError(f"Error running model: {result.get_message()}")

      process.mark_completed(result.data)
      logger.info(f"Writer agent successfully completed process {process.id}")

    except Exception as e:
      logger.exception(f"Error in WriterAgent for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process


########################################################################
#                        AGENT REGISTRATION                            #
########################################################################
def register_cli_agents(registry) -> None:
  """
  Register all CLI-specific agents with the provided registry.
  
  This demonstrates the programmatic agent registration approach using
  Registry.register() instead of pluggy extensions.
  
  Args:
      registry: The Registry instance to register agents with
  """
  logger.info("Registering CLI-specific agents")
  
  # Register the Writer agent
  registry.register(
    agent_class=WriterAgent,
    name="writer",
    description="A specialized agent for writing tasks with enhanced literary capabilities",
    required_args=None  # Uses all available kwargs
  )
  
  logger.debug("Successfully registered writer agent")

