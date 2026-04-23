"""
Sample command module for demonstration with multiple commands:
current_time, add, subtract, and echo
"""

from datetime import datetime
from typing import Dict

from .base import BaseToolModule
from ...plugins.base import ToolModuleInfo, ToolDefinition, ArgumentDefinition


class SampleModulePlugin(BaseToolModule):
  """Sample module implementing multiple utility tools."""

  info = ToolModuleInfo(
    name="sample",
    title="Sample Utilities",
    description="Sample module with utility tools for demonstration",
  )

  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    """Return all available tools in this module."""
    return {
      "current_time": ToolDefinition(
        name="current_time",
        description="Get the current UTC time in ISO format",
        callable=self._current_time,
        arguments={}
      ),

      "add": ToolDefinition(
        name="add",
        description="Add two numbers together",
        callable=self._add,
        arguments={
          "a": ArgumentDefinition(
            name="a",
            description="First number to add",
            data_type="float",
            required=True
          ),
          "b": ArgumentDefinition(
            name="b",
            description="Second number to add",
            data_type="float",
            required=True
          )
        }
      ),

      "subtract": ToolDefinition(
        name="subtract",
        description="Subtract the second number from the first",
        callable=self._subtract,
        arguments={
          "a": ArgumentDefinition(
            name="a",
            description="Number to subtract from",
            data_type="float",
            required=True
          ),
          "b": ArgumentDefinition(
            name="b",
            description="Number to subtract",
            data_type="float",
            required=True
          )
        }
      ),

      "echo": ToolDefinition(
        name="echo",
        description="Echo back the provided message",
        callable=self._echo,
        arguments={
          "message": ArgumentDefinition(
            name="message",
            description="Message to echo back",
            data_type="str",
            required=True
          )
        }
      )
    }

  def _current_time(self, **kwargs) -> str:
    return datetime.utcnow().isoformat() + "Z"

  def _add(self, a: float, b: float, **kwargs) -> str:
    result = a + b
    return f"{a} + {b} = {result}"

  def _subtract(self, a: float, b: float, **kwargs) -> str:
    result = a - b
    return f"{a} - {b} = {result}"

  def _echo(self, message: str, **kwargs) -> str:
    return str(message)
