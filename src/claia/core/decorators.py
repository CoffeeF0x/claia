"""
Decorator-based authoring sugar for CLAIA plugins.

Plugin kinds share one decorator class parameterized by an info
dataclass and an entry-point group. Applied to a class, the decorator
builds the same class-level ``info`` attribute the manager already
reads — so discovery does not change per authoring style. Applied to
a function (the ``tool`` kind only), it builds a ``ToolDefinition``
from the signature and attaches it as ``__claia_tool__``, returning
the function unwrapped.

Decorated classes are recorded into a module-level collection that
manifest discovery (``claia.plugins``) consumes. Recording is
idempotent by identity so re-imports and double decoration cannot
duplicate an entry.
"""

from __future__ import annotations

import dataclasses
import inspect
import re
import typing
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type

from .plugins.base import (
  ArgumentDefinition,
  ArchitectureInfo,
  DefinitionsInfo,
  DeploymentInfo,
  ParamSpec,
  ProtocolInfo,
  ToolDefinition,
  ToolModuleInfo,
)


########################################################################
#                              CONSTANTS                               #
########################################################################
PENDING_ATTR = "__claia_pending__"
EXPLICIT_ATTR = "__claia_explicit__"
TOOL_ATTR = "__claia_tool__"

_SCALAR_FIELDS = ("name", "title", "description")
_FUNCTION_FIELDS = frozenset({"name", "description"})
_ALLOWED_KWARGS = frozenset({"name", "title", "description", "params"})
_TYPE_NAMES = {str: "str", int: "int", float: "float", bool: "bool"}
_SPLIT_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


########################################################################
#                      MANIFEST CLASS COLLECTION                       #
########################################################################
_decorated_plugins: List[Tuple[str, type]] = []


def record_plugin(group: str, cls: type) -> None:
  """Record ``(group, cls)`` for manifest discovery.

  Appends only when that class is not already present for ``group``
  (identity check). Re-imports and applying the main decorator twice
  therefore cannot duplicate an entry.
  """
  for existing_group, existing_cls in _decorated_plugins:
    if existing_group == group and existing_cls is cls:
      return
  _decorated_plugins.append((group, cls))


def iter_decorated_plugins() -> Iterable[Tuple[str, type]]:
  """Yield ``(group, cls)`` pairs recorded by plugin decorators."""
  return tuple(_decorated_plugins)


########################################################################
#                              INFERENCE                               #
########################################################################
def _camel_to_snake(name: str) -> str:
  """Convert ``SimpleAgent`` to ``simple_agent``. No suffix stripping."""
  return _SPLIT_CAMEL.sub("_", name).lower()


def _camel_to_title(name: str) -> str:
  """Convert ``SimpleAgent`` to ``Simple Agent``. No suffix stripping."""
  return _SPLIT_CAMEL.sub(" ", name)


def _first_paragraph(obj: Any) -> str:
  """Return the first paragraph of the target's own docstring, or "".

  Reads ``__doc__`` directly rather than ``inspect.getdoc`` because the
  latter walks the MRO — a docstring-less plugin class must not inherit
  its base contract's docstring as a description.
  """
  doc = getattr(obj, "__doc__", None)
  if not doc:
    return ""
  return inspect.cleandoc(doc).split("\n\n", 1)[0].strip()


def _target_name(target: Any) -> str:
  return getattr(target, "__name__", type(target).__name__)


def _is_info_value(value: Any) -> bool:
  """True when ``value`` looks like a usable plugin ``info`` object."""
  return value is not None and not isinstance(
    value, (property, classmethod, staticmethod)
  )


def _take_pending(target: Any) -> Dict[str, Any]:
  """Pop ``__claia_pending__`` from ``target``'s own ``__dict__``."""
  if PENDING_ATTR not in target.__dict__:
    return {}
  pending = target.__dict__.get(PENDING_ATTR) or {}
  delattr(target, PENDING_ATTR)
  return pending


def _own_explicit(target: Any) -> set:
  """Return the target's own explicit-field set, creating it if needed.

  Reads ``__dict__`` so a subclass does not share its parent's set.
  """
  explicit = target.__dict__.get(EXPLICIT_ATTR)
  if explicit is None:
    explicit = set()
    setattr(target, EXPLICIT_ATTR, explicit)
  return explicit


def _own_pending(target: Any) -> Dict[str, Any]:
  """Return the target's own pending stash, creating it if needed."""
  pending = target.__dict__.get(PENDING_ATTR)
  if pending is None:
    pending = {}
    setattr(target, PENDING_ATTR, pending)
  return pending


########################################################################
#                         SIGNATURE → TOOL DEF                         #
########################################################################
def _data_type_name(hint: Any) -> str:
  return _TYPE_NAMES.get(hint, "custom")


def _parse_annotation(hint: Any) -> Tuple[str, str]:
  """Return ``(data_type, description)`` for a parameter annotation.

  ``Annotated[T, "text"]`` contributes the first string metadata
  item as the description; plain hints get an empty string.
  Unannotated parameters and anything outside
  ``str`` / ``int`` / ``float`` / ``bool`` use ``data_type="custom"``.
  """
  if hint is inspect.Parameter.empty:
    return "custom", ""
  origin = typing.get_origin(hint)
  if origin is typing.Annotated:
    args = typing.get_args(hint)
    base = args[0] if args else hint
    description = ""
    for meta in args[1:]:
      if isinstance(meta, str):
        description = meta
        break
    return _data_type_name(base), description
  return _data_type_name(hint), ""


def _tool_definition_from_signature(
  fn: Callable,
  name: str,
  description: str,
) -> ToolDefinition:
  """Build a ``ToolDefinition`` from ``fn``'s signature and hints."""
  try:
    hints = typing.get_type_hints(fn, include_extras=True)
  except Exception:
    hints = dict(getattr(fn, "__annotations__", {}))

  arguments: Dict[str, ArgumentDefinition] = {}
  for param_name, param in inspect.signature(fn).parameters.items():
    if param_name in ("self", "cls"):
      continue
    if param.kind in (
      inspect.Parameter.VAR_POSITIONAL,
      inspect.Parameter.VAR_KEYWORD,
    ):
      continue
    hint = hints.get(param_name, inspect.Parameter.empty)
    data_type, arg_description = _parse_annotation(hint)
    required = param.default is inspect.Parameter.empty
    arguments[param_name] = ArgumentDefinition(
      name=param_name,
      description=arg_description,
      data_type=data_type,
      required=required,
      default_value=None if required else param.default,
    )

  return ToolDefinition(
    name=name,
    description=description,
    callable=fn,
    arguments=arguments,
  )


########################################################################
#                         PLUGIN DECORATOR                             #
########################################################################
class PluginDecorator:
  """A plugin-kind decorator (``tool``, ``agent``, …).

  Parameterized by the info dataclass and the entry-point group the
  kind registers under. Three authoring styles produce the same
  class-level ``info``:

  - Bare ``@tool`` — every field inferred from the class.
  - Kwargs ``@tool(name=..., title=..., description=..., params=...)``.
  - Stacked modifiers (``@tool.name``, ``.title``, ``.description``,
    additive ``.param``) in either order relative to the main
    decorator. Both orders converge via a ``__claia_pending__`` stash
    when modifiers run first; a modifier that would assign a scalar
    already set by a kwarg or another modifier raises ``ValueError``.

  The ``tool`` kind also accepts functions: it builds a
  ``ToolDefinition`` and attaches it as ``__claia_tool__``. Functions
  accept only ``.name`` / ``.description``; ``.title`` or ``.param``
  raises ``ValueError``.
  """

  def __init__(
    self,
    info_cls: Type,
    group: str,
    *,
    allow_functions: bool = False,
    label: Optional[str] = None,
  ) -> None:
    self.info_cls = info_cls
    self.group = group
    self.allow_functions = allow_functions
    self.label = label or info_cls.__name__

  def __call__(self, target: Any = None, **kwargs: Any) -> Any:
    """Decorate ``target``, or return a decorator when used with kwargs.

    ``@kind`` passes the class/function as ``target``. ``@kind(...)``
    passes only keywords and returns a one-shot wrapper.
    """
    unknown = set(kwargs) - _ALLOWED_KWARGS
    if unknown:
      raise TypeError(
        f"{self.label}() got unexpected keyword argument(s): "
        f"{', '.join(sorted(unknown))}"
      )
    if target is None:
      return lambda t: self._decorate(t, kwargs)
    return self._decorate(target, kwargs)

  def name(self, value: str) -> Callable:
    """Stacked modifier that sets ``name``."""
    return self._scalar_modifier("name", value)

  def title(self, value: str) -> Callable:
    """Stacked modifier that sets ``title`` (classes only)."""
    return self._scalar_modifier("title", value)

  def description(self, value: str) -> Callable:
    """Stacked modifier that sets ``description``."""
    return self._scalar_modifier("description", value)

  def param(self, *specs: ParamSpec) -> Callable:
    """Stacked modifier that adds ``ParamSpec``s (classes only).

    Accepts one or more specs so a shared list can be spread in a
    single stage (``@architecture.param(*COMMON_TEXT_RUNTIME_PARAMS)``).
    Stacked ``.param`` stages fold in reading order — the params list
    ends up exactly as written top-down, which is what first-match-wins
    resolution (overrides declared before a spread of commons) needs.
    """
    def decorator(target: Any) -> Any:
      if inspect.isfunction(target):
        raise ValueError(".param cannot be applied to a function")
      if not inspect.isclass(target):
        raise TypeError(
          f"{self.label}.param expected a class, got {type(target).__name__}"
        )
      self._apply_param(target, specs)
      return target
    return decorator

  # ------------------------------------------------------------------
  # Dispatch
  # ------------------------------------------------------------------
  def _decorate(self, target: Any, kwargs: Dict[str, Any]) -> Any:
    if inspect.isclass(target):
      return self._decorate_class(target, kwargs)
    if inspect.isfunction(target):
      if not self.allow_functions:
        raise TypeError(
          f"{self.label} decorator cannot be applied to a function"
        )
      return self._decorate_function(target, kwargs)
    raise TypeError(
      f"{self.label} decorator expected a class"
      f"{' or function' if self.allow_functions else ''}, "
      f"got {type(target).__name__}"
    )

  def _decorate_class(self, cls: type, kwargs: Dict[str, Any]) -> type:
    pending = _take_pending(cls)
    if "info" in cls.__dict__ and not kwargs and not pending:
      record_plugin(self.group, cls)
      return cls

    pending_scalars = {
      key: pending[key] for key in _SCALAR_FIELDS if key in pending
    }
    explicit = {key for key in kwargs if key in _SCALAR_FIELDS}
    overlap = explicit & pending_scalars.keys()
    if overlap:
      field = next(iter(sorted(overlap)))
      raise ValueError(
        f"duplicate assignment of {field!r} on {_target_name(cls)}"
      )

    name = kwargs["name"] if "name" in kwargs else pending_scalars.get("name")
    if name is None:
      name = _camel_to_snake(cls.__name__)

    title = kwargs["title"] if "title" in kwargs else pending_scalars.get("title")
    if title is None:
      title = _camel_to_title(cls.__name__)

    if "description" in kwargs:
      description = kwargs["description"]
    else:
      description = pending_scalars.get("description")
    if description is None:
      description = _first_paragraph(cls)

    params = list(kwargs["params"]) if "params" in kwargs and kwargs["params"] is not None else []
    params.extend(pending.get("params") or [])

    cls.info = self.info_cls(
      name=name,
      title=title,
      description=description,
      params=params,
    )
    setattr(cls, EXPLICIT_ATTR, explicit | set(pending_scalars))
    record_plugin(self.group, cls)
    return cls

  def _decorate_function(self, fn: Callable, kwargs: Dict[str, Any]) -> Callable:
    if "title" in kwargs or "params" in kwargs:
      field = "title" if "title" in kwargs else "param"
      raise ValueError(f".{field} cannot be applied to a function")

    pending = _take_pending(fn)
    if "title" in pending or pending.get("params"):
      field = "title" if "title" in pending else "param"
      raise ValueError(f".{field} cannot be applied to a function")

    if TOOL_ATTR in fn.__dict__ and not kwargs and not pending:
      return fn

    pending_scalars = {
      key: pending[key] for key in _FUNCTION_FIELDS if key in pending
    }
    explicit = {key for key in kwargs if key in _FUNCTION_FIELDS}
    overlap = explicit & pending_scalars.keys()
    if overlap:
      field = next(iter(sorted(overlap)))
      raise ValueError(
        f"duplicate assignment of {field!r} on {_target_name(fn)}"
      )

    name = kwargs["name"] if "name" in kwargs else pending_scalars.get("name")
    if name is None:
      name = fn.__name__

    if "description" in kwargs:
      description = kwargs["description"]
    else:
      description = pending_scalars.get("description")
    if description is None:
      description = _first_paragraph(fn)

    setattr(fn, TOOL_ATTR, _tool_definition_from_signature(fn, name, description))
    setattr(fn, EXPLICIT_ATTR, explicit | set(pending_scalars))
    return fn

  # ------------------------------------------------------------------
  # Modifiers
  # ------------------------------------------------------------------
  def _scalar_modifier(self, field: str, value: Any) -> Callable:
    def decorator(target: Any) -> Any:
      if inspect.isfunction(target) and field not in _FUNCTION_FIELDS:
        raise ValueError(f".{field} cannot be applied to a function")
      if inspect.isclass(target):
        self._apply_class_scalar(target, field, value)
        return target
      if inspect.isfunction(target):
        if not self.allow_functions:
          raise TypeError(
            f"{self.label} decorator cannot be applied to a function"
          )
        self._apply_function_scalar(target, field, value)
        return target
      raise TypeError(
        f"{self.label}.{field} expected a class"
        f"{' or function' if self.allow_functions else ''}, "
        f"got {type(target).__name__}"
      )
    return decorator

  def _apply_class_scalar(self, cls: type, field: str, value: Any) -> None:
    if "info" in cls.__dict__:
      self._assign_info_field(cls, field, value)
      return
    inherited = getattr(cls, "info", None)
    if _is_info_value(inherited):
      cls.info = dataclasses.replace(inherited, params=list(inherited.params))
      self._assign_info_field(cls, field, value)
      return
    self._stash_scalar(cls, field, value)

  def _apply_function_scalar(self, fn: Callable, field: str, value: Any) -> None:
    if TOOL_ATTR in fn.__dict__:
      self._assign_tool_field(fn, field, value)
      return
    self._stash_scalar(fn, field, value)

  def _assign_info_field(self, cls: type, field: str, value: Any) -> None:
    explicit = _own_explicit(cls)
    if field in explicit:
      raise ValueError(
        f"duplicate assignment of {field!r} on {_target_name(cls)}"
      )
    setattr(cls.info, field, value)
    explicit.add(field)

  def _assign_tool_field(self, fn: Callable, field: str, value: Any) -> None:
    explicit = _own_explicit(fn)
    if field in explicit:
      raise ValueError(
        f"duplicate assignment of {field!r} on {_target_name(fn)}"
      )
    setattr(fn, TOOL_ATTR, dataclasses.replace(getattr(fn, TOOL_ATTR), **{field: value}))
    explicit.add(field)

  def _stash_scalar(self, target: Any, field: str, value: Any) -> None:
    pending = _own_pending(target)
    if field in pending:
      raise ValueError(
        f"duplicate assignment of {field!r} on {_target_name(target)}"
      )
    pending[field] = value

  def _apply_param(self, cls: type, specs: Tuple[ParamSpec, ...]) -> None:
    """Fold a ``.param`` stage's specs into the class.

    Decorators execute bottom-up, so each stage *prepends* its group:
    the stage physically closest to the class lands first and each
    stage above it slots in front, yielding reading order overall
    (within one stage the given order is kept).
    """
    if "info" in cls.__dict__:
      cls.info.params[0:0] = specs
      return
    inherited = getattr(cls, "info", None)
    if _is_info_value(inherited):
      cls.info = dataclasses.replace(inherited, params=list(inherited.params))
      cls.info.params[0:0] = specs
      return
    pending = _own_pending(cls)
    pending.setdefault("params", [])[0:0] = specs


########################################################################
#                           KIND INSTANCES                             #
########################################################################
tool = PluginDecorator(
  ToolModuleInfo, "claia.tool_modules", allow_functions=True, label="tool",
)
protocol = PluginDecorator(ProtocolInfo, "claia.tool_protocols", label="protocol")
architecture = PluginDecorator(ArchitectureInfo, "claia.architectures", label="architecture")
deployment = PluginDecorator(DeploymentInfo, "claia.deployments", label="deployment")
definitions = PluginDecorator(DefinitionsInfo, "claia.definitions", label="definitions")


__all__ = [
  "PENDING_ATTR",
  "TOOL_ATTR",
  "PluginDecorator",
  "architecture",
  "definitions",
  "deployment",
  "iter_decorated_plugins",
  "protocol",
  "record_plugin",
  "tool",
]
