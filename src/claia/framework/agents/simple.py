"""
Simple agent for CLAIA.

The default registered agent. Reads ``system`` from the call or the
queued task, composes tool instructions, then runs the tool loop.
"""

import logging

from .base import BaseAgent
from ..decorators import agent


logger = logging.getLogger(__name__)


@agent
@agent.name("simple")
@agent.title("Simple Agent")
@agent.description("A simple agent that directly calls a model for inference")
class SimpleAgent(BaseAgent):
  """A simple agent that directly calls a model for inference."""

  @classmethod
  def execute(cls, task, registry, **kwargs) -> object:
    conversation = task.conversation
    model_id = task.parameters["model_id"]
    system = kwargs.pop("system", None)
    if system is None:
      system = task.parameters.get("system")
    tag_specs = cls.resolve_tag_specs(registry, model_id)
    system = cls.compose_system_prompt(
      system,
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
      logger.exception(f"Error in SimpleAgent for {task.id}: {str(e)}")
      task.mark_failed(str(e))
    return task
