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

import logging

from ..framework.agents.base import BaseAgent


logger = logging.getLogger(__name__)


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
  """A specialized agent for writing tasks with enhanced literary capabilities."""

  @classmethod
  def execute(cls, task, registry, **kwargs) -> object:
    conversation = task.conversation
    model_id = task.parameters["model_id"]
    kwargs.pop("system", None)
    tag_specs = cls.resolve_tag_specs(registry, model_id)
    system = cls.compose_system_prompt(
      WRITER_SYSTEM_PROMPT,
      tools=registry.list_tools(),
      tag_specs=tag_specs,
    )

    try:
      last_response = ""
      for _round in range(cls.MAX_TOOL_ROUNDS):
        last_response, results, cancelled = cls.stream_turn(
          task,
          registry,
          model_id=model_id,
          system=system,
          tag_specs=tag_specs,
          **kwargs,
        )
        cls._post_tool_results(task, conversation, results)
        if cancelled:
          task.mark_cancelled(last_response)
          return task
        if not results:
          task.mark_completed(last_response)
          return task
      task.mark_completed(last_response)
    except Exception as e:
      logger.exception(f"Error in WriterAgent for {task.id}: {str(e)}")
      task.mark_failed(str(e))
    return task


def register_cli_agents(registry) -> None:
  """Register CLI-specific agents with the provided registry."""
  logger.info("Registering CLI-specific agents")

  registry.register(
    agent_class=WriterAgent,
    name="writer",
    title="Writer Agent",
    description="A specialized agent for writing tasks with enhanced literary capabilities",
  )

  logger.debug("Successfully registered writer agent")
