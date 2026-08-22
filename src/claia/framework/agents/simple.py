"""
Simple agent for CLAIA.

The default registered agent. Reads ``system`` from the call or the
queued task, then runs one chat-loop turn per step.
"""

from ...core.enums.agent import AgentStatus
from .base import BaseAgent
from ..decorators import agent


@agent
@agent.name("simple")
@agent.title("Simple Agent")
@agent.description("A simple agent that directly calls a model for inference")
class SimpleAgent(BaseAgent):
  """A simple agent that directly calls a model for inference."""

  @classmethod
  def step(cls, task, registry, **kwargs) -> AgentStatus:
    system = kwargs.pop("system", None)
    if system is None:
      system = task.parameters.get("system")
    return cls.chat_step(task, registry, system=system, **kwargs)
