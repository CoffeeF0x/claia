"""
``SimpleProtocol`` — the post-overhaul ``BaseProtocol`` impl
that bridges native ``BaseToolModule`` plugins.

The plugin is constructed at framework startup (via the
``claia.tool_protocols`` entry point) and then has the loaded tool
modules handed to it through :meth:`bind_tool_modules` once the
``Manager`` finishes wiring the ``claia.tool_modules`` group. From
there the registry rebuilds its unified tool index by asking every
protocol — including this one — for its
:class:`~claia.core.plugins.base.ToolReference` list.

Internals:

- :func:`~claia.core.tools.protocols.simple.dispatcher.find_tool`
  resolves qualified or bare names against the bound modules.
- :func:`~claia.core.tools.protocols.simple.dispatcher.prepare_command_kwargs`
  preps the callable's kwargs from a parameter dict + injectables.
- :func:`~claia.core.tools.protocols.simple.payload.decode_payload`
  decodes the ``raw_payload`` string into ``(parameters, name_hint)``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ....decorators import protocol
from ....plugins.base import ToolReference
from ....results import Result

from ..base import BaseProtocol
from .dispatcher import find_tool, normalize_result, prepare_command_kwargs
from .payload import decode_payload


logger = logging.getLogger(__name__)


@protocol
@protocol.name("simple")
@protocol.title("Simple Local Protocol")
@protocol.description("Resolves tool name to a command module plugin and executes it.")
class SimpleProtocol(BaseProtocol):
  """Bridge between native tool modules and the new protocol contract."""

  def __init__(self) -> None:
    # Bound by the framework via :meth:`bind_tool_modules` once the
    # ``Manager`` finishes loading both the protocol and the tool
    # modules. Until then the inventory looks empty, which is the
    # correct behavior for a freshly-instantiated plugin.
    self._modules: List[Any] = []

  # ------------------------------------------------------------------
  # Wiring
  # ------------------------------------------------------------------
  def bind_tool_modules(self, modules: List[Any]) -> None:
    """Attach the framework-loaded ``BaseToolModule`` instances.

    Called once by the manager after ``claia.tool_modules`` are
    instantiated; tests inject stub modules directly via this same
    setter to keep dispatch deterministic. Replaces any prior binding
    so a ``refresh`` cycle can rebuild the inventory cleanly.
    """
    self._modules = list(modules)

  @property
  def bound_modules(self) -> List[Any]:
    """Read-only view of the currently bound modules.

    Useful for diagnostics and for the transitional
    ``Registry.run_command`` path that still wants to look up tool
    definitions directly without rebuilding the dispatcher state.
    """
    return list(self._modules)

  # ------------------------------------------------------------------
  # Inventory (BaseProtocol contract)
  # ------------------------------------------------------------------
  def get_tool_references(self) -> List[ToolReference]:
    """Project each bound tool into a registry-friendly ``ToolReference``.

    The qualified name is ``"<module>.<tool>"``; the
    ``parameter_schema`` field carries the original
    ``Dict[str, ArgumentDefinition]`` map so simple-protocol-aware
    consumers (UIs, native CLI rendering) keep their introspection
    surface. The registry treats ``parameter_schema`` as opaque —
    only protocol-aware code unwraps it.
    """
    refs: List[ToolReference] = []
    for module in self._modules:
      try:
        module_info = module.info
        tools = module.get_module_tools() or {}
      except Exception:
        logger.exception("Failed to collect tools from module %r", module)
        continue

      module_name = getattr(module_info, "name", None) or ""
      for tool_name, tool_def in tools.items():
        qualified = f"{module_name}.{tool_name}" if module_name else tool_name
        refs.append(ToolReference(
          qualified_name=qualified,
          description=getattr(tool_def, "description", "") or "",
          protocol_name=self.info.name,
          parameter_schema=getattr(tool_def, "arguments", None),
        ))
    return refs

  # ------------------------------------------------------------------
  # Execute (BaseProtocol contract)
  # ------------------------------------------------------------------
  def execute(
    self,
    qualified_name: str,
    raw_payload: str,
    conversation,
    **kwargs,
  ) -> Result:
    """Dispatch ``qualified_name`` against the bound modules.

    Decodes ``raw_payload`` as JSON (flat or enveloped) into a
    parameter dict, merges ``conversation`` + cross-cutting
    ``**kwargs`` injectables on top, runs the dispatcher's kwarg-prep
    (type coercion + required validation) and finally invokes the
    callable. Any exception from the callable becomes ``Result.fail``;
    a successful return is normalized through
    :func:`~claia.core.tools.protocols.simple.dispatcher.normalize_result`.
    """
    try:
      parameters, _name_hint = decode_payload(raw_payload)
    except ValueError as exc:
      return Result.fail(f"Simple protocol: {exc}")

    found = find_tool(self._modules, qualified_name)
    if found is None:
      return Result.fail(f"Tool '{qualified_name}' not found")
    _module, tool_def = found

    extra: Dict[str, Any] = {"conversation": conversation, **kwargs}

    try:
      prepared = prepare_command_kwargs(
        parameters, tool_def, extra_kwargs=extra,
      )
    except ValueError as exc:
      return Result.fail(str(exc))

    try:
      result = tool_def.callable(**prepared)
    except Exception as exc:
      logger.exception("Error executing tool '%s'", qualified_name)
      return Result.fail(str(exc))

    return normalize_result(qualified_name, result)


__all__ = ["SimpleProtocol"]
