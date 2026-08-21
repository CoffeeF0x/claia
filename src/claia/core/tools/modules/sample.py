"""
Sample command module for demonstration with multiple commands:
current_time, add, subtract, and echo
"""

from datetime import datetime
from typing import Annotated

from .base import BaseToolModule
from ...decorators import tool


@tool
@tool.name("sample")
@tool.title("Sample Utilities")
@tool.description("Sample module with utility tools for demonstration")
class SampleModulePlugin(BaseToolModule):
  """Sample module implementing multiple utility tools."""

  @tool
  def current_time(self, **kwargs) -> str:
    """Get the current UTC time in ISO format"""
    return datetime.utcnow().isoformat() + "Z"

  @tool
  def add(
    self,
    a: Annotated[float, "First number to add"],
    b: Annotated[float, "Second number to add"],
    **kwargs,
  ) -> str:
    """Add two numbers together"""
    result = a + b
    return f"{a} + {b} = {result}"

  @tool
  def subtract(
    self,
    a: Annotated[float, "Number to subtract from"],
    b: Annotated[float, "Number to subtract"],
    **kwargs,
  ) -> str:
    """Subtract the second number from the first"""
    result = a - b
    return f"{a} - {b} = {result}"

  @tool
  def echo(self, message: Annotated[str, "Message to echo back"], **kwargs) -> str:
    """Echo back the provided message"""
    return str(message)
