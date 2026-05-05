"""
Simple protocol: bridge native ``BaseToolModule`` plugins into the
overhaul ``BaseProtocol`` contract.

Phase 4 scope (see ``docs/tools-overhaul-plan.md`` §11): this module
now implements the new :class:`BaseProtocol` ABC with the new
``execute(qualified_name, raw_payload, conversation, **kwargs)``
signature and the new :meth:`get_tool_references` inventory hook. The
actual native-tool bookkeeping (module binding, JSON payload decoding,
kwarg preparation) still lives in the registry during phase 4 and
migrates into this plugin in phase 5 along with the three-file split
(``protocol.py`` / ``dispatcher.py`` / ``payload.py``).

To keep the existing ``Registry.process_content`` tool-call flow alive
during the phase 4 / phase 5 window, the pre-overhaul dispatch logic is
preserved verbatim as :meth:`execute_legacy`. Registry code that still
walks tool spans out of assistant text calls ``execute_legacy``; the
new :meth:`execute` is the target for phase 6's agent-loop migration.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import BaseProtocol
from ...plugins.base import ProtocolInfo, ToolReference
from claia.core.results import Result


logger = logging.getLogger(__name__)


class SimpleProtocolPlugin(BaseProtocol):
  info = ProtocolInfo(
    name="simple",
    title="Simple Local Protocol",
    description="Resolves tool name to a command module plugin and executes it.",
  )

  def __init__(self) -> None:
    # Phase 5 will populate this at construction from the framework's
    # loaded tool modules. For phase 4 the registry still drives tool
    # lookup through ``execute_legacy``; the inventory hook simply
    # reflects whatever has been registered via ``bind_tool_modules``
    # (none, by default).
    self._modules: List[Any] = []

  # ------------------------------------------------------------------
  # Tool inventory
  # ------------------------------------------------------------------
  def bind_tool_modules(self, modules: List[Any]) -> None:
    """Attach the framework-loaded native tool modules to this plugin.

    Accepts the plain ``BaseToolModule`` instances exposed by pluggy
    (via the registrar's ``plugin`` passthrough). Phase 5 moves the
    authoritative binding into ``__init__`` and removes this setter.
    """
    self._modules = list(modules)

  def get_tool_references(self) -> List[ToolReference]:
    """Return one ``ToolReference`` per native tool in bound modules.

    Phase 5 replaces this walk with a three-file split; the shape is
    authoritative already so the registry's phase 5 index assembly can
    consume it unchanged.
    """
    refs: List[ToolReference] = []
    for module in self._modules:
      try:
        module_info = module.get_module_info()
        tools = module.get_module_tools() or {}
      except Exception:
        logger.exception("Failed to collect tools from module %r", module)
        continue

      module_name = getattr(module_info, "name", None) or ""
      for tool_name, tool_def in tools.items():
        qualified = f"{module_name}.{tool_name}" if module_name else tool_name
        description = getattr(tool_def, "description", "") or ""
        refs.append(ToolReference(
          qualified_name=qualified,
          description=description,
          protocol_name=self.info.name,
          parameter_schema=getattr(tool_def, "arguments", None),
        ))
    return refs

  # ------------------------------------------------------------------
  # Execute (overhaul contract)
  # ------------------------------------------------------------------
  def execute(
    self,
    qualified_name: str,
    raw_payload: str,
    conversation,
    **kwargs,
  ) -> Result:
    """Execute a native tool resolved from bound modules.

    Phase 4 delivers the minimum viable implementation: we decode
    ``raw_payload`` as JSON parameters and dispatch to the native
    callable when a matching tool is bound. The richer kwarg
    preparation + injectables path (currently in
    ``Registry._prepare_command_kwargs``) migrates here in phase 5;
    until then, callers that need the full path should go through
    ``Registry.run_command`` / ``Registry.process_content`` (which
    reach :meth:`execute_legacy`).
    """
    import json

    parameters: Dict[str, Any] = {}
    payload = (raw_payload or "").strip()
    if payload:
      try:
        decoded = json.loads(payload)
      except Exception as e:
        return Result.fail(f"Simple protocol: failed to decode JSON payload: {e}")
      if isinstance(decoded, dict):
        # Accept both the fully-envelope form ``{"name": ..., "parameters": {...}}``
        # and the flat form ``{...}`` (parameters only). A ``name`` key in the
        # envelope form is informational; the dispatch target is always
        # ``qualified_name`` as supplied by the registry.
        if "parameters" in decoded and isinstance(decoded.get("parameters"), dict):
          parameters = decoded["parameters"]
        else:
          parameters = decoded
      else:
        return Result.fail(
          "Simple protocol: JSON payload must decode to an object, got "
          f"{type(decoded).__name__}"
        )

    callable_fn, tool_def = self._resolve(qualified_name)
    if not callable_fn:
      return Result.fail(f"Tool '{qualified_name}' not found")

    try:
      # Phase 5 will route parameters through the full kwarg-prep
      # pipeline (ArgumentDefinition-driven coercion, injectables,
      # positional fallbacks). For now we pass the decoded mapping
      # directly so simple parameter-less / string-keyword tools work
      # through the new path too.
      result = callable_fn(**(parameters or {}))
    except Exception as e:
      logger.exception("Error executing tool '%s'", qualified_name)
      return Result.fail(str(e))

    return self._normalize_result(qualified_name, result)

  # ------------------------------------------------------------------
  # Legacy dispatch (transitional)
  # ------------------------------------------------------------------
  def execute_legacy(
    self,
    tool_name: str,
    parameters: Dict[str, Any],
    conversation,
    commands: Dict[str, Any],
    **kwargs,
  ) -> Result:
    """Pre-overhaul dispatch: resolve ``tool_name`` from an externally
    supplied catalog and invoke it with already-prepared kwargs.

    Kept intact so the transitional :meth:`Registry.process_content`
    flow continues to work during phase 4 / 5. Removed in phase 6
    alongside ``process_content``.
    """
    callable_fn = None

    try:
      if '.' in tool_name:
        module_name, cmd_name = tool_name.split('.', 1)
        mod = commands.get(module_name) if isinstance(commands, dict) else None
        if mod and isinstance(mod.get('list_of_tools'), list):
          for entry in mod['list_of_tools']:
            if entry.get('tool_name') == cmd_name:
              callable_fn = entry.get('tool_callable')
              break
      else:
        if isinstance(commands, dict):
          for _, mod in commands.items():
            loc = mod.get('list_of_tools') if isinstance(mod, dict) else None
            if isinstance(loc, list):
              for entry in loc:
                if entry.get('tool_name') == tool_name:
                  callable_fn = entry.get('tool_callable')
                  break
            if callable_fn:
              break

      if not callable_fn:
        return Result.fail(f"Tool '{tool_name}' not found")

      result = callable_fn(**(parameters or {}))
      return self._normalize_result(tool_name, result)
    except Exception as e:
      logger.exception(f"Error executing tool '{tool_name}'")
      return Result.fail(str(e))

  # ------------------------------------------------------------------
  # Helpers
  # ------------------------------------------------------------------
  def _resolve(self, qualified_name: str):
    """Walk bound modules looking for ``qualified_name``.

    Accepts either ``"module.tool"`` (preferred, matches the references
    we emit) or a bare tool name (first match wins across modules).
    Returns ``(callable, tool_def)`` or ``(None, None)``.
    """
    if not self._modules:
      return None, None

    module_part: Optional[str] = None
    tool_part = qualified_name
    if "." in qualified_name:
      module_part, tool_part = qualified_name.split(".", 1)

    for module in self._modules:
      try:
        module_info = module.get_module_info()
        tools = module.get_module_tools() or {}
      except Exception:
        continue
      name = getattr(module_info, "name", None) or ""
      if module_part is not None and name != module_part:
        continue
      tool_def = tools.get(tool_part)
      if tool_def is not None and callable(getattr(tool_def, "callable", None)):
        return tool_def.callable, tool_def
    return None, None

  @staticmethod
  def _normalize_result(tool_name: str, result: Any) -> Result:
    """Wrap a tool's return value in a ``Result``.

    Same behavior as pre-overhaul: ``Result`` passes through, ``str``
    wraps into ``Result.ok``, everything else fails with a typed
    diagnostic.
    """
    if isinstance(result, Result):
      return result
    if isinstance(result, str):
      return Result.ok(result)
    return Result.fail(
      f"Tool '{tool_name}' returned invalid type: {type(result).__name__}. "
      "Tools must return Result or str."
    )
