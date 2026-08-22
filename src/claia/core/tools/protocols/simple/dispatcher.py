"""
Native-tool dispatch helpers for the simple protocol.

Three concerns are split out here so the ``BaseProtocol`` impl in
``protocol.py`` and the CLI direct-execution path on
``Registry.run_command`` can share the same callable resolution and
kwarg preparation:

- :func:`find_tool` — walks the bound modules and returns
  ``(module, ToolDefinition)`` for a qualified or bare name.
- :func:`prepare_command_kwargs` — maps a parameter dict (including
  the ``__args__`` positional shorthand) plus an
  ``extra_kwargs`` injectables dict onto the callable's declared
  ``ArgumentDefinition`` schema, performing per-arg type coercion.
- :func:`normalize_result` — wraps a callable's return value in a
  ``Result``. ``Result`` passes through, ``str`` becomes
  ``Result.ok``, anything else fails with a typed diagnostic.

Kwarg-prep and type coercion live here so the registry does not
need to know about ``ArgumentDefinition``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from ....results import Result


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Type coercion
# ----------------------------------------------------------------------
def convert_type(value: Any, data_type: str) -> Any:
  """Coerce ``value`` to ``data_type`` with a tolerant best-effort.

  Supports the ``ArgumentDefinition.data_type`` set: ``'str'``,
  ``'int'``, ``'float'``, ``'bool'``, ``'custom'``. Unknown types fall
  back to ``str``. ``'custom'`` passes the value through untouched so
  tools can declare arguments holding rich Python objects (e.g. an
  injected ``settings`` instance) without going through string
  coercion.

  On a coercion failure (``int('abc')``, etc.) the raw value is
  returned so the callable can choose to validate or reject; this
  matches pre-overhaul behavior.
  """
  try:
    if data_type == "custom":
      return value
    if data_type == "int":
      return int(value)
    if data_type == "float":
      return float(value)
    if data_type == "bool":
      if isinstance(value, bool):
        return value
      v = str(value).strip().lower()
      if v in ("1", "true", "t", "yes", "y", "on"):
        return True
      if v in ("0", "false", "f", "no", "n", "off"):
        return False
      return bool(v)
    return str(value)
  except Exception:
    return value


# ----------------------------------------------------------------------
# Kwarg preparation
# ----------------------------------------------------------------------
def prepare_command_kwargs(
  parameters: Dict[str, Any],
  tool_def: Any,
  extra_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
  """Map ``parameters`` to the callable's expected kwargs.

  Resolution per declared argument (highest precedence first):

  1. Explicit ``parameters[name]``.
  2. Matching name in ``extra_kwargs`` (host injectables, the
     conversation, etc.).
  3. The next positional value from the magic ``__args__`` list under
     ``parameters`` (CLI-style positional support).
  4. ``arg_def.default_value`` when set.

  Required arguments without a value raise ``ValueError``; the caller
  is expected to translate that into a ``Result.fail``.

  Insertion order of ``tool_def.arguments`` determines the positional
  pop order — Python 3.7+ preserves dict order, which is exactly what
  the CLI relies on.
  """
  args_spec = getattr(tool_def, "arguments", None) or {}

  pos_vals: list = []
  if (
    isinstance(parameters, dict)
    and "__args__" in parameters
    and isinstance(parameters["__args__"], list)
  ):
    pos_vals = list(parameters["__args__"])

  filtered_extra = extra_kwargs or {}
  call_kwargs: Dict[str, Any] = {}

  for name, arg_def in args_spec.items():
    provided: Any = None

    if isinstance(parameters, dict) and name in parameters:
      provided = parameters[name]
    elif name in filtered_extra:
      provided = filtered_extra[name]
    elif pos_vals:
      provided = pos_vals.pop(0)
    elif (
      hasattr(arg_def, "default_value")
      and getattr(arg_def, "default_value") is not None
    ):
      provided = getattr(arg_def, "default_value")

    required = getattr(arg_def, "required", False)
    if provided is None and required:
      raise ValueError(f"Missing required argument: {name}")

    if provided is not None:
      dtype = getattr(arg_def, "data_type", "str")
      call_kwargs[name] = convert_type(provided, dtype)

  return call_kwargs


# ----------------------------------------------------------------------
# Module / tool resolution
# ----------------------------------------------------------------------
def find_tool(modules, qualified_name: str) -> Optional[Tuple[Any, Any]]:
  """Walk ``modules`` looking for ``qualified_name``.

  Returns ``(module, ToolDefinition)`` or ``None``. Accepts:

  - ``"module.tool"`` — the canonical qualified form emitted by
    :meth:`SimpleProtocol.get_tool_references`.
  - ``"tool"`` (bare) — first match across all modules wins.

  Modules whose ``info`` / ``get_module_tools`` raise are
  skipped; one broken module must not poison the whole walk.
  """
  if not modules:
    return None

  module_part: Optional[str] = None
  tool_part = qualified_name
  if "." in qualified_name:
    module_part, tool_part = qualified_name.split(".", 1)

  for module in modules:
    try:
      module_info = module.info
      tools = module.get_module_tools() or {}
    except Exception:
      logger.exception("Failed to introspect module %r", module)
      continue

    name = getattr(module_info, "name", None) or ""
    if module_part is not None and name != module_part:
      continue

    tool_def = tools.get(tool_part)
    if tool_def is not None and callable(getattr(tool_def, "callable", None)):
      return module, tool_def

  return None


# ----------------------------------------------------------------------
# Result normalization
# ----------------------------------------------------------------------
def normalize_result(qualified_name: str, value: Any) -> Result:
  """Wrap a callable's return value in a ``Result``.

  ``Result`` passes through unchanged, ``str`` becomes ``Result.ok``,
  every other type triggers a ``Result.fail`` with a typed diagnostic
  so contract violations surface loudly. Same semantics as the
  pre-overhaul ``SimpleProtocol.execute``.
  """
  if isinstance(value, Result):
    return value
  if isinstance(value, str):
    return Result.ok(value)
  return Result.fail(
    f"Tool '{qualified_name}' returned invalid type: "
    f"{type(value).__name__}. Tools must return Result or str."
  )


__all__ = [
  "convert_type",
  "find_tool",
  "normalize_result",
  "prepare_command_kwargs",
]
