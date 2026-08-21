"""
Abstract base class for tool modules.

A tool module groups one or more callable tools (commands) under a
common namespace. Each tool is described by a ``ToolDefinition`` that
declares its callable, description, and arguments.

Subclasses declare their metadata via a class-level ``info`` attribute
so plugin discovery does not have to instantiate the plugin.
"""

from abc import ABC
from dataclasses import replace
from typing import ClassVar, Dict

from ...plugins.base import ToolModuleInfo, ToolDefinition


class BaseToolModule(ABC):
  """Contract for tool-module plugins."""

  info: ClassVar[ToolModuleInfo]

  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    """Return the tools provided by this module keyed by tool name.

    Default implementation scans ``type(self)`` for attributes marked
    by the ``tool`` decorator (``__claia_tool__``) and rebinds each
    ``ToolDefinition.callable`` to the instance. Subclasses may still
    override with a hand-built mapping; a module with neither
    decorated methods nor an override yields an empty dict.
    """
    tools: Dict[str, ToolDefinition] = {}
    cls = type(self)
    for attr_name in dir(cls):
      attr = getattr(cls, attr_name, None)
      defn = getattr(attr, "__claia_tool__", None)
      if defn is None:
        continue
      tools[defn.name] = replace(defn, callable=getattr(self, attr_name))
    return tools
