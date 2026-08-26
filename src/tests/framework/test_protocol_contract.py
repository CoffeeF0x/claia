"""
Protocol contract tests.

Exercises the protocol contract described in the ExoFox docs repo
``claia/overview.md`` Decisions:

- ``ToolReference`` dataclass shape and defaults.
- ``BaseProtocol`` ABC (abstract method enforcement, default
  lifecycle no-ops, class-level ``info``).
- ``SimpleProtocol`` implementing the ABC: ``execute`` via
  JSON payload and ``get_tool_references`` reflecting bound modules.
- ``Manager`` lifecycle: ``start()`` fires at load time,
  ``stop_protocols()`` / ``refresh_protocols()`` iterate loaded
  protocols and swallow per-plugin errors.
- ``Registry.refresh_tools`` / ``Registry.shutdown`` surface the
  lifecycle entry points without tripping over unloaded plugins.
"""

from __future__ import annotations

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
from claia.core.tools.protocols.simple import SimpleProtocol


# ---------------------------------------------------------------------------
# ToolReference
# ---------------------------------------------------------------------------
class TestToolReference:
  """The registry's protocol-agnostic tool descriptor."""

  def test_required_fields_construct_with_defaults(self):
    ref = ToolReference(
      qualified_name="system.exit",
      description="Exit the application.",
      protocol_name="simple",
    )
    assert ref.qualified_name == "system.exit"
    assert ref.description == "Exit the application."
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

    assert core_exported is ToolReference
    assert framework_exported is ToolReference


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

  def test_info_is_reachable_from_instance(self):
    class Minimal(BaseProtocol):
      info = ProtocolInfo(name="m", title="M", description="D")

      def get_tool_references(self) -> List[ToolReference]:
        return []

      def execute(self, qualified_name, raw_payload, conversation, **kwargs):
        return Result.ok("noop")

    inst = Minimal()
    assert inst.info is Minimal.info
    assert inst.info.name == "m"


# ---------------------------------------------------------------------------
# SimpleProtocol
# ---------------------------------------------------------------------------
def _make_module(module_name: str, tools: Dict[str, Any]):
  """Construct a minimal ``BaseToolModule``-compatible duck."""
  class _Module:
    info = ToolModuleInfo(name=module_name, title=module_name, description="")

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


class TestSimpleProtocolContract:
  """``SimpleProtocol`` honors the new ``BaseProtocol`` ABC."""

  def test_is_concrete_instantiable_and_info_matches(self):
    plugin = SimpleProtocol()
    info = plugin.info
    assert info.name == "simple"
    assert info.title.startswith("Simple")

  def test_get_tool_references_empty_when_no_modules_bound(self):
    plugin = SimpleProtocol()
    assert plugin.get_tool_references() == []

  def test_get_tool_references_emits_qualified_names(self):
    plugin = SimpleProtocol()

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
    plugin = SimpleProtocol()

    class _Broken:
      @property
      def info(self):
        raise RuntimeError("boom")

      def get_module_tools(self):  # pragma: no cover - unreachable
        return {}

    plugin.bind_tool_modules([_Broken()])
    assert plugin.get_tool_references() == []

  def test_execute_returns_not_found_without_modules(self):
    plugin = SimpleProtocol()
    result = plugin.execute("demo.echo", "{}", conversation=None)
    assert result.is_error()
    assert "demo.echo" in result.get_message()

  def test_execute_dispatches_from_json_payload(self):
    plugin = SimpleProtocol()

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
    plugin = SimpleProtocol()

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
    plugin = SimpleProtocol()
    plugin.bind_tool_modules([
      _make_module("demo", {"echo": _tool_def("echo", lambda **_: "ok")}),
    ])

    result = plugin.execute("demo.echo", "not-json{", conversation=None)
    assert result.is_error()
    assert "JSON" in result.get_message()

  def test_execute_rejects_non_object_payload(self):
    plugin = SimpleProtocol()
    plugin.bind_tool_modules([
      _make_module("demo", {"echo": _tool_def("echo", lambda **_: "ok")}),
    ])

    result = plugin.execute("demo.echo", "[1, 2, 3]", conversation=None)
    assert result.is_error()
    assert "object" in result.get_message()

  def test_execute_handles_empty_payload(self):
    plugin = SimpleProtocol()

    def _ping() -> Result:
      return Result.ok("pong")

    plugin.bind_tool_modules([
      _make_module("demo", {"ping": _tool_def("ping", _ping)}),
    ])

    result = plugin.execute("demo.ping", "", conversation=None)
    assert result.is_success()
    assert result.get_data() == "pong"

  def test_execute_wraps_string_return_in_result_ok(self):
    plugin = SimpleProtocol()
    plugin.bind_tool_modules([
      _make_module("demo", {"greet": _tool_def("greet", lambda: "hello")}),
    ])
    result = plugin.execute("demo.greet", "", conversation=None)
    assert result.is_success()
    assert result.get_data() == "hello"

  def test_execute_fails_on_invalid_return_type(self):
    plugin = SimpleProtocol()
    plugin.bind_tool_modules([
      _make_module("demo", {"bad": _tool_def("bad", lambda: 42)}),
    ])
    result = plugin.execute("demo.bad", "", conversation=None)
    assert result.is_error()
    assert "invalid type" in result.get_message()

  def test_execute_translates_callable_exception(self):
    plugin = SimpleProtocol()

    def _boom():
      raise RuntimeError("kaboom")

    plugin.bind_tool_modules([
      _make_module("demo", {"boom": _tool_def("boom", _boom)}),
    ])
    result = plugin.execute("demo.boom", "", conversation=None)
    assert result.is_error()
    assert "kaboom" in result.get_message()


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
  """Manager wires protocol lifecycle hooks."""

  def _inject_protocols(self, manager, protocols):
    """Populate the manager's lazy-plugin table directly for tests.

    Avoids entry-point discovery so the tests don't depend on
    installed entry points or package state.
    """
    from claia.framework.manager import PluginEntry

    entries = {}
    for proto in protocols:
      entry = PluginEntry(
        name=proto.info.name,
        group="claia.tool_protocols",
        entry_point=None,
        plugin_class=type(proto),
        info=proto.info,
      )
      entry.instance = proto
      key = proto.info.name
      suffix = 1
      while key in entries:
        suffix += 1
        key = f"{proto.info.name}-{suffix}"
      entries[key] = entry
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
    ):
      manager._lazy_plugins[group] = {}

    with patch.object(manager, "_load_plugins", wraps=lambda group, label, allow_empty=False: None):
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
    # ``refresh_tools`` invalidates the unified ``_tool_index`` /
    # ``_protocols_by_name`` so the next access rebuilds them from
    # the post-refresh inventories.
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
