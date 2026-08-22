"""
Simple protocol and registry tool-index tests.

Exercises the plumbing that lives in
``claia.core.tools.protocols.simple`` and the tool-index surface on
``Registry``:

- The ``payload.decode_payload`` helper accepts both flat and
  envelope JSON shapes and rejects everything else with ``ValueError``.
- The ``dispatcher`` helpers — ``convert_type``, ``find_tool``,
  ``prepare_command_kwargs``, ``normalize_result`` — drive both
  ``SimpleProtocol.execute`` and ``Registry.run_command``.
- ``SimpleProtocol`` still resolves at the same package path
  the entry point already uses, so the on-disk split is invisible to
  the framework.
- ``Manager`` binds native tool modules into the simple protocol
  during ``load_all_plugins`` and exposes a public
  ``iter_protocol_instances`` accessor for the registry.
- ``Registry`` builds a unified ``_tool_index`` /
  ``_protocols_by_name`` view from the protocol inventory, exposes
  ``list_tools`` / ``get_tool`` / ``execute_tool``, applies
  first-in-list-wins on collisions, invalidates the index on
  ``refresh_tools``, and routes ``run_command`` through the shared
  dispatcher helpers.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

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
from claia.core.tools.protocols.simple.dispatcher import (
  convert_type,
  find_tool,
  normalize_result,
  prepare_command_kwargs,
)
from claia.core.tools.protocols.simple.payload import decode_payload


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
def _make_module(module_name: str, tools: Dict[str, ToolDefinition]):
  class _Module:
    info = ToolModuleInfo(name=module_name, title=module_name, description="")

    def get_module_tools(self) -> Dict[str, ToolDefinition]:
      return tools

  return _Module()


def _tool(tool_name: str, fn, arg_defs: Dict[str, ArgumentDefinition] = None) -> ToolDefinition:
  return ToolDefinition(
    name=tool_name,
    description=f"tool {tool_name}",
    callable=fn,
    arguments=arg_defs or {},
  )


# ---------------------------------------------------------------------------
# Package layout / entry-point compatibility
# ---------------------------------------------------------------------------
class TestSimpleProtocolPackageLayout:
  """The package split must not break the existing entry point."""

  def test_simple_module_exposes_plugin_class(self):
    import claia.core.tools.protocols.simple as simple_pkg

    assert hasattr(simple_pkg, "SimpleProtocol")
    assert simple_pkg.SimpleProtocol is SimpleProtocol

  def test_internal_split_imports(self):
    from claia.core.tools.protocols.simple import dispatcher, payload, protocol

    assert hasattr(dispatcher, "prepare_command_kwargs")
    assert hasattr(dispatcher, "find_tool")
    assert hasattr(dispatcher, "normalize_result")
    assert hasattr(dispatcher, "convert_type")
    assert hasattr(payload, "decode_payload")
    assert protocol.SimpleProtocol is SimpleProtocol

  def test_simple_protocol_still_subclass_of_base(self):
    assert issubclass(SimpleProtocol, BaseProtocol)


# ---------------------------------------------------------------------------
# payload.decode_payload
# ---------------------------------------------------------------------------
class TestDecodePayload:
  def test_empty_payload_returns_empty_dict(self):
    assert decode_payload("") == ({}, None)

  def test_whitespace_only_payload_returns_empty_dict(self):
    assert decode_payload("   \n\t") == ({}, None)

  def test_flat_object_returns_parameters_with_no_name_hint(self):
    params, name = decode_payload('{"a": 1, "b": "x"}')
    assert params == {"a": 1, "b": "x"}
    assert name is None

  def test_envelope_unwraps_parameters_and_surfaces_name(self):
    params, name = decode_payload(
      '{"name": "demo.echo", "parameters": {"msg": "hi"}}'
    )
    assert params == {"msg": "hi"}
    assert name == "demo.echo"

  def test_envelope_with_non_string_name_drops_hint(self):
    params, name = decode_payload(
      '{"name": 42, "parameters": {"msg": "hi"}}'
    )
    assert params == {"msg": "hi"}
    assert name is None

  def test_envelope_without_parameters_treated_as_flat(self):
    """``parameters`` missing => the object itself is the parameter dict."""
    params, name = decode_payload('{"name": "demo.echo", "msg": "hi"}')
    assert params == {"name": "demo.echo", "msg": "hi"}
    assert name is None

  def test_envelope_with_non_dict_parameters_treated_as_flat(self):
    """``parameters`` not a dict => fall through to flat handling."""
    params, name = decode_payload('{"parameters": "string", "x": 1}')
    assert params == {"parameters": "string", "x": 1}
    assert name is None

  def test_invalid_json_raises_value_error(self):
    with pytest.raises(ValueError, match="failed to decode JSON"):
      decode_payload("{not json")

  def test_non_object_json_raises_value_error(self):
    with pytest.raises(ValueError, match="must decode to an object"):
      decode_payload("[1, 2, 3]")

  def test_string_json_raises_value_error(self):
    with pytest.raises(ValueError, match="must decode to an object"):
      decode_payload('"just a string"')


# ---------------------------------------------------------------------------
# dispatcher.convert_type
# ---------------------------------------------------------------------------
class TestConvertType:
  def test_int_string_to_int(self):
    assert convert_type("42", "int") == 42

  def test_float_string_to_float(self):
    assert convert_type("3.14", "float") == 3.14

  def test_bool_truthy_strings(self):
    for raw in ("true", "1", "yes", "on", "y", "t", "TRUE", "  Yes "):
      assert convert_type(raw, "bool") is True, raw

  def test_bool_falsy_strings(self):
    for raw in ("false", "0", "no", "off", "n", "f", "FALSE", "  No "):
      assert convert_type(raw, "bool") is False, raw

  def test_bool_pass_through_native(self):
    assert convert_type(True, "bool") is True
    assert convert_type(False, "bool") is False

  def test_bool_unknown_string_falls_back_to_truthiness(self):
    # Non-empty unknown string -> True (matches pre-overhaul behavior).
    assert convert_type("maybe", "bool") is True

  def test_str_default(self):
    assert convert_type(42, "str") == "42"
    assert convert_type("hi", "str") == "hi"

  def test_unknown_data_type_falls_back_to_str(self):
    assert convert_type(42, "weirdtype") == "42"

  def test_custom_passes_through(self):
    sentinel = object()
    assert convert_type(sentinel, "custom") is sentinel

  def test_invalid_int_returns_raw_value(self):
    """Coercion failure must not raise; the callable can validate later."""
    assert convert_type("not-an-int", "int") == "not-an-int"


# ---------------------------------------------------------------------------
# dispatcher.find_tool
# ---------------------------------------------------------------------------
class TestFindTool:
  def test_returns_none_for_empty_modules(self):
    assert find_tool([], "demo.x") is None
    assert find_tool(None, "demo.x") is None

  def test_qualified_name_resolves_to_specific_module(self):
    a = _make_module("a", {"echo": _tool("echo", lambda: "from-a")})
    b = _make_module("b", {"echo": _tool("echo", lambda: "from-b")})
    found = find_tool([a, b], "b.echo")
    assert found is not None
    _module, tool_def = found
    assert tool_def.callable() == "from-b"

  def test_bare_name_resolves_first_match(self):
    a = _make_module("a", {"echo": _tool("echo", lambda: "from-a")})
    b = _make_module("b", {"echo": _tool("echo", lambda: "from-b")})
    found = find_tool([a, b], "echo")
    assert found is not None
    _module, tool_def = found
    assert tool_def.callable() == "from-a"

  def test_unknown_qualified_name_returns_none(self):
    a = _make_module("a", {"echo": _tool("echo", lambda: "ok")})
    assert find_tool([a], "a.missing") is None
    assert find_tool([a], "missing.echo") is None

  def test_skips_module_that_raises_during_introspection(self):
    class _Broken:
      @property
      def info(self):
        raise RuntimeError("boom")

      def get_module_tools(self):  # pragma: no cover
        return {}

    a = _make_module("a", {"echo": _tool("echo", lambda: "ok")})
    found = find_tool([_Broken(), a], "a.echo")
    assert found is not None

  def test_skips_tool_def_without_callable(self):
    bad = _make_module("a", {
      "broken": ToolDefinition(name="broken", description="", callable=None, arguments={}),  # type: ignore[arg-type]
    })
    assert find_tool([bad], "a.broken") is None


# ---------------------------------------------------------------------------
# dispatcher.prepare_command_kwargs
# ---------------------------------------------------------------------------
class TestPrepareCommandKwargs:
  def _tool_def_with_args(self, **arg_defs: ArgumentDefinition):
    return ToolDefinition(
      name="t", description="", callable=lambda **_: None, arguments=arg_defs,
    )

  def test_explicit_parameters_take_precedence_over_extras(self):
    td = self._tool_def_with_args(
      name=ArgumentDefinition(name="name", description="", data_type="str", required=True),
    )
    out = prepare_command_kwargs(
      {"name": "alice"}, td, extra_kwargs={"name": "bob"},
    )
    assert out == {"name": "alice"}

  def test_extras_fill_in_when_parameter_missing(self):
    td = self._tool_def_with_args(
      conversation=ArgumentDefinition(
        name="conversation", description="", data_type="custom", required=False,
      ),
    )
    sentinel = object()
    out = prepare_command_kwargs({}, td, extra_kwargs={"conversation": sentinel})
    assert out == {"conversation": sentinel}

  def test_positional_args_consumed_in_declaration_order(self):
    td = self._tool_def_with_args(
      first=ArgumentDefinition(name="first", description="", data_type="str", required=True),
      second=ArgumentDefinition(name="second", description="", data_type="str", required=False),
    )
    out = prepare_command_kwargs(
      {"__args__": ["A", "B"]}, td,
    )
    assert out == {"first": "A", "second": "B"}

  def test_default_values_apply_when_no_other_source(self):
    td = self._tool_def_with_args(
      kind=ArgumentDefinition(
        name="kind", description="", data_type="str", required=False,
        default_value="text",
      ),
    )
    out = prepare_command_kwargs({}, td)
    assert out == {"kind": "text"}

  def test_required_argument_without_value_raises(self):
    td = self._tool_def_with_args(
      name=ArgumentDefinition(name="name", description="", data_type="str", required=True),
    )
    with pytest.raises(ValueError, match="Missing required argument: name"):
      prepare_command_kwargs({}, td)

  def test_type_coercion_applied_after_resolution(self):
    td = self._tool_def_with_args(
      count=ArgumentDefinition(name="count", description="", data_type="int", required=True),
      flag=ArgumentDefinition(name="flag", description="", data_type="bool", required=True),
    )
    out = prepare_command_kwargs({"count": "5", "flag": "yes"}, td)
    assert out == {"count": 5, "flag": True}

  def test_optional_argument_without_value_omitted(self):
    td = self._tool_def_with_args(
      maybe=ArgumentDefinition(
        name="maybe", description="", data_type="str", required=False,
      ),
    )
    out = prepare_command_kwargs({}, td)
    assert out == {}


# ---------------------------------------------------------------------------
# dispatcher.normalize_result
# ---------------------------------------------------------------------------
class TestNormalizeResult:
  def test_result_passes_through(self):
    src = Result.ok("payload")
    assert normalize_result("t", src) is src

  def test_str_wrapped_in_ok(self):
    out = normalize_result("t", "hello")
    assert out.is_success()
    assert out.get_data() == "hello"

  def test_invalid_type_fails(self):
    out = normalize_result("t", 42)
    assert out.is_error()
    assert "invalid type" in out.get_message()
    assert "int" in out.get_message()


# ---------------------------------------------------------------------------
# SimpleProtocol under the new layout
# ---------------------------------------------------------------------------
class TestSimpleProtocolIntegration:
  def test_get_tool_references_after_bind(self):
    plugin = SimpleProtocol()
    plugin.bind_tool_modules([
      _make_module("demo", {"ping": _tool("ping", lambda: Result.ok("pong"))}),
    ])
    refs = plugin.get_tool_references()
    assert len(refs) == 1
    assert refs[0].qualified_name == "demo.ping"
    assert refs[0].protocol_name == "simple"

  def test_bind_tool_modules_replaces_prior_modules(self):
    plugin = SimpleProtocol()
    plugin.bind_tool_modules([
      _make_module("first", {"x": _tool("x", lambda: "old")}),
    ])
    plugin.bind_tool_modules([
      _make_module("second", {"y": _tool("y", lambda: "new")}),
    ])
    refs = [r.qualified_name for r in plugin.get_tool_references()]
    assert refs == ["second.y"]

  def test_bound_modules_property_is_read_only_view(self):
    plugin = SimpleProtocol()
    src = [_make_module("demo", {})]
    plugin.bind_tool_modules(src)
    snapshot = plugin.bound_modules
    snapshot.append("intruder")  # type: ignore[arg-type]
    # Plugin's internal list is unchanged.
    assert len(plugin.bound_modules) == 1

  def test_execute_runs_callable_via_payload_then_dispatcher(self):
    """Smoke test: the new ``execute`` path uses ``decode_payload``,
    ``find_tool``, ``prepare_command_kwargs``, and ``normalize_result``."""
    plugin = SimpleProtocol()

    captured: Dict[str, Any] = {}

    def _greet(name: str, conversation=None) -> Result:
      captured["name"] = name
      captured["conversation"] = conversation
      return Result.ok(f"hi {name}")

    plugin.bind_tool_modules([
      _make_module("demo", {
        "greet": _tool(
          "greet", _greet,
          {
            "name": ArgumentDefinition(
              name="name", description="", data_type="str", required=True,
            ),
            "conversation": ArgumentDefinition(
              name="conversation", description="", data_type="custom",
              required=False,
            ),
          },
        ),
      }),
    ])

    sentinel_conv = object()
    result = plugin.execute(
      "demo.greet",
      '{"name": "world"}',
      conversation=sentinel_conv,
    )
    assert result.is_success()
    assert result.get_data() == "hi world"
    assert captured["name"] == "world"
    assert captured["conversation"] is sentinel_conv

  def test_execute_propagates_required_arg_error(self):
    plugin = SimpleProtocol()
    plugin.bind_tool_modules([
      _make_module("demo", {
        "greet": _tool(
          "greet", lambda name: f"hi {name}",
          {
            "name": ArgumentDefinition(
              name="name", description="", data_type="str", required=True,
            ),
          },
        ),
      }),
    ])
    result = plugin.execute("demo.greet", "{}", conversation=None)
    assert result.is_error()
    assert "Missing required argument" in result.get_message()


# ---------------------------------------------------------------------------
# Manager binding + iteration accessor
# ---------------------------------------------------------------------------
class TestManagerBinding:
  def test_iter_protocol_instances_is_public(self):
    """``Registry`` reaches for the public accessor; verify it exists."""
    from claia.framework.manager import Manager

    manager = Manager()
    assert hasattr(manager, "iter_protocol_instances")
    assert callable(manager.iter_protocol_instances)

  def test_bind_native_tools_to_protocols_hands_modules_over(self):
    from claia.framework.manager import Manager, PluginEntry

    manager = Manager()
    plugin = SimpleProtocol()

    # Inject one tool module + the simple protocol directly.
    proto_entry = PluginEntry(
      name="simple", group="claia.tool_protocols", entry_point=None,
      plugin_class=type(plugin), info=plugin.info,
    )
    proto_entry.instance = plugin

    fake_module = _make_module("demo", {"ping": _tool("ping", lambda: "pong")})
    mod_entry = PluginEntry(
      name="demo", group="claia.tool_modules", entry_point=None,
      plugin_class=type(fake_module),
    )
    mod_entry.instance = fake_module

    manager._lazy_plugins["claia.tool_protocols"] = {proto_entry.name: proto_entry}
    manager._lazy_plugins["claia.tool_modules"] = {mod_entry.name: mod_entry}

    manager._bind_native_tools_to_protocols()

    assert plugin.bound_modules == [fake_module]
    refs = plugin.get_tool_references()
    assert [r.qualified_name for r in refs] == ["demo.ping"]

  def test_bind_swallows_protocol_errors(self):
    """A failing binder must not break other protocols."""
    from claia.framework.manager import Manager, PluginEntry

    class _BadBinder(BaseProtocol):
      info = ProtocolInfo(name="bad", title="B", description="")

      def get_tool_references(self):
        return []

      def execute(self, qualified_name, raw_payload, conversation, **kwargs):
        return Result.fail("unused")

      def bind_tool_modules(self, modules):
        raise RuntimeError("nope")

    manager = Manager()
    bad = _BadBinder()
    good = SimpleProtocol()

    bad_entry = PluginEntry(
      name="bad", group="claia.tool_protocols", entry_point=None,
      plugin_class=type(bad), info=bad.info,
    )
    bad_entry.instance = bad
    good_entry = PluginEntry(
      name="simple", group="claia.tool_protocols", entry_point=None,
      plugin_class=type(good), info=good.info,
    )
    good_entry.instance = good
    manager._lazy_plugins["claia.tool_protocols"] = {
      bad_entry.name: bad_entry,
      good_entry.name: good_entry,
    }

    fake_module = _make_module("demo", {"ping": _tool("ping", lambda: "pong")})
    mod_entry = PluginEntry(
      name="demo", group="claia.tool_modules", entry_point=None,
      plugin_class=type(fake_module),
    )
    mod_entry.instance = fake_module
    manager._lazy_plugins["claia.tool_modules"] = {mod_entry.name: mod_entry}

    manager._bind_native_tools_to_protocols()
    # Good binder still received its modules.
    assert good.bound_modules == [fake_module]


# ---------------------------------------------------------------------------
# Registry: index + execute_tool
# ---------------------------------------------------------------------------
class _StubProtocol(BaseProtocol):
  """Concrete BaseProtocol whose inventory is settable in tests."""

  def __init__(self, name: str, refs: List[ToolReference]):
    # Instance-level ``info`` so each stub can use a distinct name
    # without sharing a class attribute.
    self.info = ProtocolInfo(name=name, title=name, description="")
    self._refs = refs
    self.execute_calls: List[Dict[str, Any]] = []

  def get_tool_references(self) -> List[ToolReference]:
    return list(self._refs)

  def execute(self, qualified_name, raw_payload, conversation, **kwargs):
    call = {
      "qualified_name": qualified_name,
      "raw_payload": raw_payload,
      "conversation": conversation,
      "kwargs": kwargs,
    }
    self.execute_calls.append(call)
    return Result.ok(f"{self.info.name}:{qualified_name}")


def _registry_with_protocols(monkeypatch, protocols: List[BaseProtocol]):
  """Construct a real ``Registry`` whose manager is stubbed to expose
  the supplied protocols (and otherwise behaves as a no-op)."""
  from claia.framework.manager import Manager as RealManager
  import claia.framework.registry as registry_module

  class _FakeManager:
    coerce_value = staticmethod(RealManager.coerce_value)
    filter_init_kwargs = staticmethod(RealManager.filter_init_kwargs)
    filter_runtime_kwargs = staticmethod(RealManager.filter_runtime_kwargs)
    resolve_runtime_kwargs = staticmethod(RealManager.resolve_runtime_kwargs)
    validate_required_init_kwargs = staticmethod(RealManager.validate_required_init_kwargs)
    _COERCE_FAIL = RealManager._COERCE_FAIL
    _mask_for_log = staticmethod(RealManager._mask_for_log)

    def __init__(self):
      self._refresh_calls = 0
      self._stop_calls = 0

    def discover_plugins(self):
      return None

    def load_all_plugins(self, **kwargs):
      return None

    def iter_protocol_instances(self):
      yield from protocols

    def refresh_protocols(self):
      self._refresh_calls += 1

    def stop_protocols(self):
      self._stop_calls += 1

    def get_all_commands(self):
      return {}

  monkeypatch.setattr(registry_module, "Manager", _FakeManager)
  reg = registry_module.Registry()
  reg._plugins_loaded = True
  return reg


class TestRegistryToolIndex:
  def test_list_tools_aggregates_references_across_protocols(self, monkeypatch):
    a = _StubProtocol("alpha", [
      ToolReference(qualified_name="alpha.one", description="", protocol_name="alpha"),
    ])
    b = _StubProtocol("beta", [
      ToolReference(qualified_name="beta.one", description="", protocol_name="beta"),
      ToolReference(qualified_name="beta.two", description="", protocol_name="beta"),
    ])
    reg = _registry_with_protocols(monkeypatch, [a, b])
    refs = {r.qualified_name for r in reg.list_tools()}
    assert refs == {"alpha.one", "beta.one", "beta.two"}

  def test_get_tool_returns_none_for_unknown_name(self, monkeypatch):
    a = _StubProtocol("alpha", [])
    reg = _registry_with_protocols(monkeypatch, [a])
    assert reg.get_tool("missing") is None

  def test_first_in_list_wins_on_duplicate_qualified_names(self, monkeypatch):
    a = _StubProtocol("alpha", [
      ToolReference(qualified_name="shared.tool", description="from-alpha", protocol_name="alpha"),
    ])
    b = _StubProtocol("beta", [
      ToolReference(qualified_name="shared.tool", description="from-beta", protocol_name="beta"),
    ])
    reg = _registry_with_protocols(monkeypatch, [a, b])
    ref = reg.get_tool("shared.tool")
    assert ref is not None
    assert ref.protocol_name == "alpha"
    assert ref.description == "from-alpha"

  def test_execute_tool_routes_to_owning_protocol(self, monkeypatch):
    a = _StubProtocol("alpha", [
      ToolReference(qualified_name="alpha.one", description="", protocol_name="alpha"),
    ])
    b = _StubProtocol("beta", [
      ToolReference(qualified_name="beta.one", description="", protocol_name="beta"),
    ])
    reg = _registry_with_protocols(monkeypatch, [a, b])

    res_a = reg.execute_tool("alpha.one", '{"x": 1}', None, flag=True)
    res_b = reg.execute_tool("beta.one", '{"y": 2}', None)

    assert res_a.is_success()
    assert res_a.get_data() == "alpha:alpha.one"
    assert a.execute_calls == [{
      "qualified_name": "alpha.one",
      "raw_payload": '{"x": 1}',
      "conversation": None,
      "kwargs": {"flag": True},
    }]

    assert res_b.is_success()
    assert res_b.get_data() == "beta:beta.one"
    assert b.execute_calls[0]["qualified_name"] == "beta.one"

  def test_execute_tool_unknown_name_returns_fail(self, monkeypatch):
    reg = _registry_with_protocols(monkeypatch, [_StubProtocol("alpha", [])])
    res = reg.execute_tool("nope.nope", "{}", None)
    assert res.is_error()
    assert "Tool not found" in res.get_message()

  def test_execute_tool_protocol_exception_becomes_failure(self, monkeypatch):
    class _Boom(BaseProtocol):
      info = ProtocolInfo(name="boom", title="B", description="")

      def get_tool_references(self):
        return [ToolReference(qualified_name="boom.x", description="", protocol_name="boom")]

      def execute(self, qualified_name, raw_payload, conversation, **kwargs):
        raise RuntimeError("kaboom")

    reg = _registry_with_protocols(monkeypatch, [_Boom()])
    res = reg.execute_tool("boom.x", "{}", None)
    assert res.is_error()
    assert "kaboom" in res.get_message()

  def test_refresh_tools_invalidates_index(self, monkeypatch):
    a = _StubProtocol("alpha", [
      ToolReference(qualified_name="alpha.one", description="", protocol_name="alpha"),
    ])
    reg = _registry_with_protocols(monkeypatch, [a])

    # Force initial build.
    assert len(reg.list_tools()) == 1
    assert reg._tool_index is not None

    # Mutate the protocol's inventory so the rebuild has different data.
    a._refs = [
      ToolReference(qualified_name="alpha.one", description="", protocol_name="alpha"),
      ToolReference(qualified_name="alpha.two", description="", protocol_name="alpha"),
    ]
    reg.refresh_tools()
    assert reg._tool_index is None  # invalidated
    assert reg._protocols_by_name is None
    assert {r.qualified_name for r in reg.list_tools()} == {"alpha.one", "alpha.two"}

  def test_refresh_tools_noop_before_load(self, monkeypatch):
    a = _StubProtocol("alpha", [])
    reg = _registry_with_protocols(monkeypatch, [a])
    reg._plugins_loaded = False
    reg.manager.refresh_protocols = MagicMock()
    reg.refresh_tools()
    reg.manager.refresh_protocols.assert_not_called()


class TestRegistryRunCommandThroughDispatcher:
  """``run_command`` now uses the simple protocol's dispatcher helpers
  rather than its own private kwarg-prep machinery."""

  def test_run_command_uses_dispatcher_prepare_kwargs(self, monkeypatch):
    """Verify the dispatcher helpers are reached and host injectables
    flow through correctly."""
    from claia.framework.manager import Manager as RealManager
    import claia.framework.registry as registry_module

    captured: Dict[str, Any] = {}

    def _impl(name, registry, settings, conversation):
      captured.update(
        name=name, registry=registry, settings=settings, conversation=conversation,
      )
      return Result.ok(f"hi {name}")

    tool_def = ToolDefinition(
      name="greet",
      description="",
      callable=_impl,
      arguments={
        "name": ArgumentDefinition(name="name", description="", data_type="str", required=True),
        "registry": ArgumentDefinition(name="registry", description="", data_type="custom", required=False),
        "settings": ArgumentDefinition(name="settings", description="", data_type="custom", required=False),
        "conversation": ArgumentDefinition(name="conversation", description="", data_type="custom", required=False),
      },
    )

    class _FakeManager:
      coerce_value = staticmethod(RealManager.coerce_value)
      filter_init_kwargs = staticmethod(RealManager.filter_init_kwargs)
      filter_runtime_kwargs = staticmethod(RealManager.filter_runtime_kwargs)
      resolve_runtime_kwargs = staticmethod(RealManager.resolve_runtime_kwargs)
      validate_required_init_kwargs = staticmethod(RealManager.validate_required_init_kwargs)
      _COERCE_FAIL = RealManager._COERCE_FAIL
      _mask_for_log = staticmethod(RealManager._mask_for_log)

      def discover_plugins(self): return None
      def load_all_plugins(self, **kwargs): return None
      def iter_protocol_instances(self): return iter(())

      def get_tool_by_name(self, command_name):
        return object(), tool_def, None

    monkeypatch.setattr(registry_module, "Manager", _FakeManager)
    reg = registry_module.Registry()
    reg._plugins_loaded = True

    settings_sentinel = object()
    reg.set_tool_context(settings=settings_sentinel)

    sentinel_conv = object()
    result = reg.run_command(
      "demo.greet",
      {"name": "world"},
      sentinel_conv,
    )

    assert result.is_success()
    assert result.get_data() == "hi world"
    assert captured["name"] == "world"
    assert captured["registry"] is reg
    assert captured["settings"] is settings_sentinel
    assert captured["conversation"] is sentinel_conv

  def test_run_command_returns_fail_for_unknown_tool(self, monkeypatch):
    from claia.framework.manager import Manager as RealManager
    import claia.framework.registry as registry_module

    class _FakeManager:
      coerce_value = staticmethod(RealManager.coerce_value)
      filter_init_kwargs = staticmethod(RealManager.filter_init_kwargs)
      filter_runtime_kwargs = staticmethod(RealManager.filter_runtime_kwargs)
      resolve_runtime_kwargs = staticmethod(RealManager.resolve_runtime_kwargs)
      validate_required_init_kwargs = staticmethod(RealManager.validate_required_init_kwargs)
      _COERCE_FAIL = RealManager._COERCE_FAIL
      _mask_for_log = staticmethod(RealManager._mask_for_log)

      def discover_plugins(self): return None
      def load_all_plugins(self, **kwargs): return None
      def iter_protocol_instances(self): return iter(())

      def get_tool_by_name(self, command_name):
        return None, None, None

    monkeypatch.setattr(registry_module, "Manager", _FakeManager)
    reg = registry_module.Registry()
    reg._plugins_loaded = True

    res = reg.run_command("missing", {}, None)
    assert res.is_error()
    assert "Tool not found" in res.get_message()


# ---------------------------------------------------------------------------
# Cleanup verification
# ---------------------------------------------------------------------------
class TestRegistryNoLongerOwnsKwargPrep:
  """The registry does not own ``ArgumentDefinition`` or kwarg prep."""

  def test_registry_lacks_prepare_command_kwargs(self):
    from claia.framework.registry import Registry

    assert not hasattr(Registry, "_prepare_command_kwargs")
    assert not hasattr(Registry, "_convert_type")

  def test_registry_lacks_commands_catalog_cache(self):
    from claia.framework.registry import Registry

    reg = Registry.__new__(Registry)
    # The attribute was removed; only the new index attrs exist now.
    assert not hasattr(reg, "_commands_catalog")
