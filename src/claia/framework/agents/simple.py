"""
Simple agent for CLAIA.

The default registered agent. Uses ``BaseAgent.execute`` as-is: stream,
parse tags, dispatch tools, generate again. Persona comes from the
caller ``system`` / task parameter, or the default helpful-assistant
prompt.
"""

from .base import BaseAgent
from ..decorators import agent


@agent
@agent.name("simple")
@agent.title("Simple Agent")
@agent.description("A simple agent that directly calls a model for inference")
class SimpleAgent(BaseAgent):
  """A simple agent that directly calls a model for inference."""
