"""
System commands module providing basic terminal controls like clear and exit.
"""

import os
from typing import Dict
import pluggy

from claia.hooks.tool import ToolModuleInfo, ToolDefinition, ArgumentDefinition


hookimpl = pluggy.HookimplMarker("claia_tool_modules")


class SystemModulePlugin:
  """System module implementing terminal utilities."""

  @hookimpl
  def get_module_info(self) -> ToolModuleInfo:
    return ToolModuleInfo(
      name="system",
      title="System Utilities",
      description="Clear the screen or exit the application",
    )

  @hookimpl
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
    # Use ANSI escape as portable clear; fallback to OS commands
    try:
      # ANSI clear screen + move cursor home
      print("\033[2J\033[H", end="", flush=True)
    except Exception:
      # Fallbacks: not expected in normal terminals
      os.system("cls" if os.name == "nt" else "clear")
    return ""

  def _exit(self, **kwargs) -> Dict[str, str]:
    # Return a structured signal; CLI should interpret and exit gracefully
    return {"action": "exit", "message": "Goodbye"}
