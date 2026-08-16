"""
Phase 4 — Protocol contract rewrite tests.

Exercises the post-overhaul protocol contract described in
the ExoFox docs repo ``claia/tools-overhaul-plan.md`` §6:

- ``ToolReference`` dataclass shape and defaults.
- New ``BaseProtocol`` ABC (abstract method enforcement, default
  lifecycle no-ops, ``get_protocol_info`` passthrough).
- ``SimpleProtocolPlugin`` implementing the new ABC: ``execute`` via
  JSON payload and ``get_tool_references`` reflecting bound modules.
- ``ProtocolRegistrar`` wiring the new hooks through to the plugin.
- ``Manager`` lifecycle: ``start()`` fires at load time,
  ``stop_protocols()`` / ``refresh_protocols()`` iterate loaded
  protocols and swallow per-plugin errors.
- ``Registry.refresh_tools`` / ``Registry.shutdown`` surface the
  lifecycle entry points without tripping over unloaded plugins.
- Deprecation banner on the legacy ABC import.

Note: the phase 5 ``execute_legacy`` shim and the corresponding
``Registry.process_content`` flow were retired in phase 6; tests that
covered them have been removed alongside the production code.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from claia.core.plugins.base import (
  ArgumentDefinition,
  ProtocolInfo,
  ToolDefinition,
  ToolModuleInfo,
  ToolReference,
)
from claia.core.results import Result
from claia.core.tools.protocols.base import BaseProtocol
from claia.core.tools.protocols.simple import SimpleProtocolPlugin
from claia.framework.hooks.protocol import ProtocolHooks
from claia.framework.registrars import ProtocolRegistrar


# ---------------------------------------------------------------------------
# ToolReference
# ---------------------------------------------------------------------------
class TestToolReference:
  """The registry's protocol-agnostic tool descriptor."""

  def test_required_fields_construct_with_defaults(self):
    ref = ToolReference(
      qualified_name="system.clear",
      description="Clear the active conversation.",
      protocol_name="simple",
    )
    assert ref.qualified_name == "system.clear"
    assert ref.description == "Clear the active conversation."
    assert ref.protocol_name == "simple"
    assert ref.parameter_schema is None
    assert ref.tags == []

  def test_parameter_schema_is_opaque_any(self):
    schema = {"foo": ArgumentDefinition(
      name="foo", description="", data_type="str", required=True,
    )}
    ref = ToolReference(
      qualified_name="simple.foo",
      description="",
      protocol_name="simple",
      parameter_schema=schema,
    )
    assert ref.parameter_schema is schema

  def test_tags_default_is_fresh_list_per_instance(self):
    a = ToolReference(qualified_name="a", description="", protocol_name="p")
    b = ToolReference(qualified_name="b", description="", protocol_name="p")
    a.tags.append("x")
    assert b.tags == [], "dataclass field default_factory must not share state"

  def test_exports_from_public_surfaces(self):
    from claia.core.plugins import ToolReference as core_exported
    from claia.framework import ToolReference as framework_exported
    from claia.framework.hooks import ToolReference as hooks_exported

    assert core_exported is ToolReference
    assert framework_exported is ToolReference
    assert hooks_exported is ToolReference


# ---------------------------------------------------------------------------
# BaseProtocol ABC
# ---------------------------------------------------------------------------
class TestBaseProtocolContract:
  """The new ABC that protocol plugins subclass."""

  def test_abstract_methods_prevent_direct_instantiation(self):
    with pytest.raises(TypeError):
      BaseProtocol()  # type: ignore[abstract]

  def test_concrete_subclass_without_execute_is_abstract(self):
    class Incomplete(BaseProtocol):
      info = ProtocolInfo(name="x", title="X", description="")

      def get_tool_references(self) -> List[ToolReference]:
        return []

    with pytest.raises(TypeError):
      Incomplete()  # type: ignore[abstract]

  def test_default_lifecycle_methods_are_noops(self):
    class Minimal(BaseProtocol):
      info = ProtocolInfo(name="m", title="M", description="")

      def get_tool_references(self) -> List[ToolReference]:
        return []

      def execute(self, qualified_name, raw_payload, conversation, **kwargs):
        return Result.ok("noop")

    inst = Minimal()
    assert inst.start() is None
    assert inst.stop() is None
    assert inst.refresh() is None

  def test_get_protocol_info_returns_class_info(self):
    class Minimal(BaseProtocol):
      info = ProtocolInfo(name="m", title="M", description="D")

      def get_tool_references(self) -> List[ToolReference]:
        return []

      def execute(self, qualified_name, raw_payload, conversation, **kwargs):
        return Result.ok("noop")

    inst = Minimal()
    retrieved = inst.get_protocol_info()
    assert retrieved is Minimal.info
    assert retrieved.name == "m"


# ---------------------------------------------------------------------------
# Legacy ABC deprecation banner
# ---------------------------------------------------------------------------
class TestLegacyProtocolDeprecation:
  """The pre-overhaul contract is kept importable with a deprecation."""

  def test_importing_legacy_module_warns(self):
    import importlib
    import sys

    sys.modules.pop("claia.core.tools.protocols._legacy", None)
    with warnings.catch_warnings(record=True) as caught:
      warnings.simplefilter("always")
      importlib.import_module("claia.core.tools.protocols._legacy")

    banner = [
      w for w in caught
      if issubclass(w.category, DeprecationWarning)
      and "LegacyBaseProtocol" in str(w.message)
    ]
    assert banner, f"expected LegacyBaseProtocol deprecation warning, got {caught}"

  def test_subclassing_legacy_emits_warning(self):
    from claia.core.tools.protocols._legacy import LegacyBaseProtocol

    with warnings.catch_warnings(record=True) as caught:
      warnings.simplefilter("always")

      class _Dummy(LegacyBaseProtocol):
        info = ProtocolInfo(name="dummy", title="Dummy", description="")

        def execute(self, tool_name, parameters, conversation, commands, **kwargs):
          return Result.ok("dummy")

      # Silence Ruff about unused class — we just want the warning.
      assert _Dummy is not None

    triggered = [
      w for w in caught
      if issubclass(w.category, DeprecationWarning)
      and "_Dummy" in str(w.message)
    ]
    assert triggered, "subclass creation must trigger DeprecationWarning"


# ---------------------------------------------------------------------------
# SimpleProtocolPlugin
# ---------------------------------------------------------------------------
def _make_module(module_name: str, tools: Dict[str, Any]):
  """Construct a minimal ``BaseToolModule``-compatible duck."""
  class _Module:
    def get_module_info(self) -> ToolModuleInfo:
      return ToolModuleInfo(name=module_name, title=module_name, description="")

    def get_module_tools(self):
      return tools

  return _Module()


def _tool_def(name: str, fn, **arg_defs: ArgumentDefinition) -> ToolDefinition:
  return ToolDefinition(
    name=name,
    description=f"tool {name}",
    callable=fn,
    arguments=arg_defs,
  )


class TestSimpleProtocolPluginContract:
  """``SimpleProtocolPlugin`` honors the new ``BaseProtocol`` ABC."""

  def test_is_concrete_instantiable_and_info_matches(self):
    plugin = SimpleProtocolPlugin()
    info = plugin.get_protocol_info()
    assert info.name == "simple"
    assert info.title.startswith("Simple")

  def test_get_tool_references_empty_when_no_modules_bound(self):
    plugin = SimpleProtocolPlugin()
    assert plugin.get_tool_references() == []

  def test_get_tool_references_emits_qualified_names(self):
    plugin = SimpleProtocolPlugin()

    def _echo(message: str) -> Result:
      return Result.ok(message)

    module = _make_module("demo", {
      "echo": _tool_def(
        "echo", _echo,
        message=ArgumentDefinition(
          name="message", description="", data_type="str", required=True,
        ),
      ),
    })
    plugin.bind_tool_modules([module])

    refs = plugin.get_tool_references()
    assert len(refs) == 1
    ref = refs[0]
    assert ref.qualified_name == "demo.echo"
    assert ref.description == "tool echo"
    assert ref.protocol_name == "simple"
    assert "message" in ref.parameter_schema

  def test_get_tool_references_tolerates_module_failure(self):
    plugin = SimpleProtocolPlugin()

    class _Broken:
      def get_module_info(self):
        raise RuntimeError("boom")

      def get_module_tools(self):  # pragma: no cover - unreachable
        return {}

    plugin.bind_tool_modules([_Broken()])
    assert plugin.get_tool_references() == []

  def test_execute_returns_not_found_without_modules(self):
    plugin = SimpleProtocolPlugin()
    result = plugin.execute("demo.echo", "{}", conversation=None)
    assert result.is_error()
    assert "demo.echo" in result.get_message()

  def test_execute_dispatches_from_json_payload(self):
    plugin = SimpleProtocolPlugin()

    def _echo(message: str) -> Result:
      return Result.ok(f"echo:{message}")

    plugin.bind_tool_modules([
      _make_module("demo", {
        "echo": _tool_def(
          "echo", _echo,
          message=ArgumentDefinition(
            name="message", description="", data_type="str", required=True,
          ),
        ),
      }),
    ])

    result = plugin.execute("demo.echo", '{"message": "hi"}', conversation=None)
    assert result.is_success()
    assert result.get_data() == "echo:hi"

  def test_execute_accepts_envelope_payload(self):
    plugin = SimpleProtocolPlugin()

    def _add(a: int, b: int) -> str:
      return str(a + b)

    plugin.bind_tool_modules([
      _make_module("math", {
        "add": _tool_def(
          "add", _add,
          a=ArgumentDefinition(name="a", description="", data_type="int", required=True),
          b=ArgumentDefinition(name="b", description="", data_type="int", required=True),
        ),
      }),
    ])

    result = plugin.execute(
      "math.add",
      '{"name": "math.add", "parameters": {"a": 2, "b": 3}}',
      conversation=None,
    )
    assert result.is_success()
    assert result.get_data() == "5"

  def test_execute_rejects_non_json_payload(self):
    plugin = SimpleProtocolPlugin()
    plugin.bind_tool_modules([
      _make_module("demo", {"echo": _tool_def("echo", lambda **_: "ok")}),
    ])

    result = plugin.execute("demo.echo", "not-json{", conversation=None)
    assert result.is_error()
    assert "JSON" in result.get_message()

  def test_execute_rejects_non_object_payload(self):
    plugin = SimpleProtocolPlugin()
    plugin.bind_tool_modules([
      _make_module("demo", {"echo": _tool_def("echo", lambda **_: "ok")}),
    ])

    result = plugin.execute("demo.echo", "[1, 2, 3]", conversation=None)
    assert result.is_error()
    assert "object" in result.get_message()

  def test_execute_handles_empty_payload(self):
    plugin = SimpleProtocolPlugin()

    def _ping() -> Result:
      return Result.ok("pong")

    plugin.bind_tool_modules([
      _make_module("demo", {"ping": _tool_def("ping", _ping)}),
    ])

    result = plugin.execute("demo.ping", "", conversation=None)
    assert result.is_success()
    assert result.get_data() == "pong"

  def test_execute_wraps_string_return_in_result_ok(self):
    plugin = SimpleProtocolPlugin()
    plugin.bind_tool_modules([
      _make_module("demo", {"greet": _tool_def("greet", lambda: "hello")}),
    ])
    result = plugin.execute("demo.greet", "", conversation=None)
    assert result.is_success()
    assert result.get_data() == "hello"

  def test_execute_fails_on_invalid_return_type(self):
    plugin = SimpleProtocolPlugin()
    plugin.bind_tool_modules([
      _make_module("demo", {"bad": _tool_def("bad", lambda: 42)}),
    ])
    result = plugin.execute("demo.bad", "", conversation=None)
    assert result.is_error()
    assert "invalid type" in result.get_message()

  def test_execute_translates_callable_exception(self):
    plugin = SimpleProtocolPlugin()

    def _boom():
      raise RuntimeError("kaboom")

    plugin.bind_tool_modules([
      _make_module("demo", {"boom": _tool_def("boom", _boom)}),
    ])
    result = plugin.execute("demo.boom", "", conversation=None)
    assert result.is_error()
    assert "kaboom" in result.get_message()


# ---------------------------------------------------------------------------
# ProtocolRegistrar
# ---------------------------------------------------------------------------
class TestProtocolRegistrar:
  """The pluggy adapter around ``BaseProtocol`` forwards every hook."""

  def test_registrar_delegates_all_lifecycle_methods(self):
    plugin = MagicMock(spec=[
      "get_protocol_info", "start", "stop", "refresh",
      "get_tool_references", "execute",
    ])
    plugin.get_protocol_info.return_value = ProtocolInfo(
      name="mock", title="Mock", description="",
    )
    plugin.get_tool_references.return_value = [
      ToolReference(qualified_name="mock.one", description="", protocol_name="mock"),
    ]
    plugin.execute.return_value = Result.ok("ran")

    reg = ProtocolRegistrar(plugin)

    info = reg.get_protocol_info()
    assert info.name == "mock"

    reg.start(); reg.stop(); reg.refresh()
    plugin.start.assert_called_once()
    plugin.stop.assert_called_once()
    plugin.refresh.assert_called_once()

    refs = reg.get_tool_references()
    assert [r.qualified_name for r in refs] == ["mock.one"]

    result = reg.execute(
      qualified_name="mock.one",
      raw_payload='{"x": 1}',
      conversation=None,
      custom_kwarg="abc",
    )
    plugin.execute.assert_called_once_with(
      qualified_name="mock.one",
      raw_payload='{"x": 1}',
      conversation=None,
      custom_kwarg="abc",
    )
    assert result.get_data() == "ran"

  def test_registrar_execute_forwards_kwargs_only(self):
    """``execute`` delegates via keyword args so plugins can rely on
    keyword parameters matching the contract."""
    captured: Dict[str, Any] = {}

    class _Plugin(BaseProtocol):
      info = ProtocolInfo(name="cap", title="C", description="")

      def get_tool_references(self):
        return []

      def execute(self, qualified_name, raw_payload, conversation, **kwargs):
        captured.update(
          qualified_name=qualified_name,
          raw_payload=raw_payload,
          kwargs=kwargs,
        )
        return Result.ok("done")

    reg = ProtocolRegistrar(_Plugin())
    reg.execute("cap.x", "{}", None, flag=True)
    assert captured["qualified_name"] == "cap.x"
    assert captured["raw_payload"] == "{}"
    assert captured["kwargs"] == {"flag": True}


# ---------------------------------------------------------------------------
# ProtocolHooks signatures
# ---------------------------------------------------------------------------
class TestProtocolHooksSignatures:
  """The pluggy hookspec mirrors the new ABC."""

  def test_hookspec_declares_all_lifecycle_hooks(self):
    declared = {
      name for name in dir(ProtocolHooks)
      if not name.startswith("_")
    }
    assert {
      "get_protocol_info",
      "start",
      "stop",
      "refresh",
      "get_tool_references",
      "execute",
    } <= declared

  def test_execute_signature_uses_new_parameters(self):
    import inspect
    params = list(inspect.signature(ProtocolHooks.execute).parameters)
    assert params[:4] == ["self", "qualified_name", "raw_payload", "conversation"]


# ---------------------------------------------------------------------------
# Manager lifecycle integration
# ---------------------------------------------------------------------------
class _TrackingProtocol(BaseProtocol):
  """BaseProtocol subclass that records every lifecycle call for tests."""

  info = ProtocolInfo(name="tracker", title="Tracker", description="")

  def __init__(self):
    self.calls: List[str] = []

  def start(self):
    self.calls.append("start")

  def stop(self):
    self.calls.append("stop")

  def refresh(self):
    self.calls.append("refresh")

  def get_tool_references(self):
    return [
      ToolReference(qualified_name="tracker.noop", description="", protocol_name="tracker"),
    ]

  def execute(self, qualified_name, raw_payload, conversation, **kwargs):
    return Result.ok("tracker")


class _BrokenProtocol(BaseProtocol):
  """Lifecycle methods raise; used to verify the Manager swallows errors."""

  info = ProtocolInfo(name="broken", title="Broken", description="")

  def start(self):
    raise RuntimeError("start boom")

  def stop(self):
    raise RuntimeError("stop boom")

  def refresh(self):
    raise RuntimeError("refresh boom")

  def get_tool_references(self):
    return []

  def execute(self, qualified_name, raw_payload, conversation, **kwargs):
    return Result.fail("broken")


class TestManagerProtocolLifecycle:
  """Manager wires protocol lifecycle hooks (plan §11 Phase 4 bullet 5)."""

  def _inject_protocols(self, manager, protocols):
    """Populate the manager's lazy-plugin table directly for tests.

    Avoids pluggy entry-point discovery so the tests don't depend on
    installed entry points or package state.
    """
    from claia.framework.manager import PluginEntry

    entries = []
    for proto in protocols:
      entry = PluginEntry(
        name=proto.info.name,
        group="claia.tool_protocols",
        entry_point=None,
        plugin_class=type(proto),
        info=proto.info,
      )
      entry.instance = proto
      entries.append(entry)
    manager._lazy_plugins["claia.tool_protocols"] = entries

  def test_start_fires_at_load_time(self):
    from claia.framework.manager import Manager

    manager = Manager()
    tracker = _TrackingProtocol()

    # Pretend discovery already ran so load_all_plugins skips metadata
    # collection.
    manager._plugins_discovered = True
    # Other groups start empty; load_all_plugins will log-warn for
    # missing required architectures, so stub that path out.
    self._inject_protocols(manager, [tracker])
    for group in (
      'claia.definitions', 'claia.tool_modules',
      'claia.agents', 'claia.architectures', 'claia.deployments',
      'claia.solvers',
    ):
      manager._lazy_plugins[group] = []

    with patch.object(manager, "_load_plugins", wraps=lambda group, pm, label, allow_empty=False, ctor_kwargs=None: None):
      manager.load_all_plugins()

    assert tracker.calls == ["start"]

  def test_stop_protocols_dispatches_across_loaded_protocols(self):
    from claia.framework.manager import Manager

    manager = Manager()
    t1 = _TrackingProtocol()
    t2 = _TrackingProtocol()
    self._inject_protocols(manager, [t1, t2])

    manager.stop_protocols()
    assert t1.calls == ["stop"]
    assert t2.calls == ["stop"]

  def test_refresh_protocols_dispatches_across_loaded_protocols(self):
    from claia.framework.manager import Manager

    manager = Manager()
    tracker = _TrackingProtocol()
    self._inject_protocols(manager, [tracker])

    manager.refresh_protocols()
    assert tracker.calls == ["refresh"]

  def test_lifecycle_swallows_protocol_errors(self):
    from claia.framework.manager import Manager

    manager = Manager()
    tracker = _TrackingProtocol()
    broken = _BrokenProtocol()
    self._inject_protocols(manager, [broken, tracker])

    # Must not raise even though ``broken`` throws in every lifecycle
    # method. The tracker should still observe its own calls.
    manager._start_protocols()
    manager.refresh_protocols()
    manager.stop_protocols()

    assert tracker.calls == ["start", "refresh", "stop"]


# ---------------------------------------------------------------------------
# Registry surface
# ---------------------------------------------------------------------------
class TestRegistryRefreshAndShutdown:
  """Registry exposes the new lifecycle entry points."""

  def test_refresh_tools_noop_before_plugin_load(self):
    from claia.framework.registry import Registry

    # The registry constructor runs ``discover_plugins`` but not load.
    registry = Registry()
    registry.manager.refresh_protocols = MagicMock()

    registry.refresh_tools()
    registry.manager.refresh_protocols.assert_not_called()

  def test_refresh_tools_delegates_to_manager_and_invalidates_cache(self):
    from claia.framework.registry import Registry

    registry = Registry()
    registry._plugins_loaded = True
    # Phase 5: ``_commands_catalog`` is gone; ``refresh_tools`` instead
    # invalidates the unified ``_tool_index`` / ``_protocols_by_name``
    # so the next access rebuilds them from the post-refresh
    # inventories.
    registry._tool_index = {"stale.tool": object()}  # type: ignore[assignment]
    registry._protocols_by_name = {"simple": object()}
    registry.manager.refresh_protocols = MagicMock()

    registry.refresh_tools()
    registry.manager.refresh_protocols.assert_called_once()
    assert registry._tool_index is None
    assert registry._protocols_by_name is None

  def test_shutdown_tears_down_workers_and_protocols(self):
    from claia.framework.registry import Registry

    registry = Registry()
    registry._plugins_loaded = True
    registry.manager.stop_protocols = MagicMock()
    registry.stop_workers = MagicMock()

    registry.shutdown()
    registry.stop_workers.assert_called_once()
    registry.manager.stop_protocols.assert_called_once()

  def test_shutdown_skips_protocols_when_plugins_never_loaded(self):
    from claia.framework.registry import Registry

    registry = Registry()
    registry._plugins_loaded = False
    registry.manager.stop_protocols = MagicMock()
    registry.stop_workers = MagicMock()

    registry.shutdown()
    registry.stop_workers.assert_called_once()
    registry.manager.stop_protocols.assert_not_called()
