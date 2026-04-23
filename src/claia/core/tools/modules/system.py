"""
System commands module providing basic terminal controls like clear and exit.
"""

import os
from typing import Dict

from .base import BaseToolModule
from ...plugins.base import ToolModuleInfo, ToolDefinition
from claia.core.results import Result


class SystemModulePlugin(BaseToolModule):
  """System module implementing terminal utilities."""

  info = ToolModuleInfo(
    name="system",
    title="System Utilities",
    description="Clear the screen or exit the application",
  )

  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    return {
      "clear": ToolDefinition(
        name="clear",
        description="Clear the terminal screen",
        callable=self._clear,
        arguments={}
      ),
      "exit": ToolDefinition(
        name="exit",
        description="Exit the application",
        callable=self._exit,
        arguments={}
      ),
    }

  def _clear(self, **kwargs) -> str:
    try:
      print("\033[2J\033[H", end="", flush=True)
    except Exception:
      os.system("cls" if os.name == "nt" else "clear")
    return ""

  def _exit(self, **kwargs) -> Result:
    return Result.shutdown(message="Goodbye", exit=True, exit_code=0)
