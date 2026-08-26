"""
System commands module providing application controls like exit.
"""

from .base import BaseToolModule
from ...decorators import tool
from ...results import Result


@tool
@tool.name("system")
@tool.title("System Utilities")
@tool.description("Exit the application")
class SystemToolModule(BaseToolModule):
  """System module implementing application controls."""

  @tool
  def exit(self, **kwargs) -> Result:
    """Exit the application"""
    return Result.shutdown(message="Goodbye", exit=True, exit_code=0)
