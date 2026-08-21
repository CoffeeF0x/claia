"""
System commands module providing basic terminal controls like clear and exit.
"""

import os

from .base import BaseToolModule
from ...decorators import tool
from ...results import Result


@tool
@tool.name("system")
@tool.title("System Utilities")
@tool.description("Clear the screen or exit the application")
class SystemModulePlugin(BaseToolModule):
  """System module implementing terminal utilities."""

  @tool
  def clear(self, **kwargs) -> str:
    """Clear the terminal screen"""
    try:
      print("\033[2J\033[H", end="", flush=True)
    except Exception:
      os.system("cls" if os.name == "nt" else "clear")
    return ""

  @tool
  def exit(self, **kwargs) -> Result:
    """Exit the application"""
    return Result.shutdown(message="Goodbye", exit=True, exit_code=0)
