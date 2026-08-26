"""
Tests for decorator-based plugin authoring (core kinds).

Covers the three class styles (bare / kwargs / stacked), both
stacking orders, duplicate-scalar errors, inherited-info
copy-on-write, function-tool inference, illegal function modifiers,
and the default ``get_module_tools`` binding.
"""

from typing import Annotated

import pytest

from claia.core.decorators import (
  PENDING_ATTR,
  _decorated_plugins,
  iter_decorated_plugins,
  protocol,
  record_plugin,
  tool,
)
from claia.core.plugins.base import ParamSpec, ProtocolInfo, ToolModuleInfo
from claia.core.tools.modules.base import BaseToolModule
from claia.core.tools.modules.sample import SampleToolModule
from claia.core.tools.modules.system import SystemToolModule


########################################################################
#                              FIXTURES                                #
########################################################################
@pytest.fixture(autouse=True)
def _restore_decorated_plugins():
  """Keep the manifest collection from leaking across tests."""
  snapshot = list(_decorated_plugins)
  try:
    yield
  finally:
    _decorated_plugins[:] = snapshot


def _info_fields(info):
  return (info.name, info.title, info.description, list(info.params))


########################################################################
#                         CLASS AUTHORING STYLES                       #
########################################################################
def test_bare_class_infers_name_title_and_first_paragraph():
  @tool
  class BareCalculator(BaseToolModule):
    """A bare calculator.

    Extra paragraph that must not become the description.
    """

  assert isinstance(BareCalculator.info, ToolModuleInfo)
  assert BareCalculator.info.name == "bare_calculator"
  assert BareCalculator.info.title == "Bare Calculator"
  assert BareCalculator.info.description == "A bare calculator."
  assert BareCalculator.info.params == []


def test_bare_class_without_docstring_gets_empty_description():
  @tool
  class NoDocPlugin:
    pass

  assert NoDocPlugin.info.name == "no_doc_plugin"
  assert NoDocPlugin.info.title == "No Doc Plugin"
  assert NoDocPlugin.info.description == ""


def test_docstringless_subclass_does_not_inherit_base_docstring():
  @tool
  class NoDocModule(BaseToolModule):
    pass

  assert NoDocModule.info.description == ""


def test_kwargs_map_onto_info_fields():
  spec = ParamSpec(name="precision", type=int, default=2)

  @tool(
    name="calc",
    title="Calculator",
    description="Does math",
    params=[spec],
  )
  class Calculator(BaseToolModule):
    """Ignored because description was given."""

  assert _info_fields(Calculator.info) == (
    "calc", "Calculator", "Does math", [spec],
  )


def test_stacked_orders_converge_on_identical_info():
  spec = ParamSpec(name="precision", type=int, default=2)

  @tool
  @tool.param(spec)
  @tool.description("Does math")
  @tool.title("Calculator")
  @tool.name("calc")
  class OrderModifiersFirst(BaseToolModule):
    """Ignored."""

  @tool.param(spec)
  @tool.description("Does math")
  @tool.title("Calculator")
  @tool.name("calc")
  @tool
  class OrderMainFirst(BaseToolModule):
    """Ignored."""

  assert _info_fields(OrderModifiersFirst.info) == _info_fields(OrderMainFirst.info)
  assert OrderModifiersFirst.info.name == "calc"
  assert OrderModifiersFirst.info.title == "Calculator"
  assert OrderModifiersFirst.info.description == "Does math"
  assert OrderModifiersFirst.info.params == [spec]


def test_param_stages_fold_in_reading_order():
  first = ParamSpec(name="precision", type=int, default=2)
  second = ParamSpec(name="mode", type=str, default="fast")

  @tool
  @tool.param(first)
  @tool.param(second)
  class WithParams(BaseToolModule):
    """Has params."""

  assert WithParams.info.params == [first, second]

  @tool.param(first)
  @tool.param(second)
  @tool
  class WithParamsMainFirst(BaseToolModule):
    """Has params."""

  assert WithParamsMainFirst.info.params == [first, second]


def test_param_stage_accepts_spread_and_keeps_override_first():
  override = ParamSpec(name="max_tokens", type=int, default=4000)
  commons = [
    ParamSpec(name="max_tokens", type=int, default=1000),
    ParamSpec(name="temperature", type=float, default=0.7),
  ]

  @tool
  @tool.param(override)
  @tool.param(*commons)
  class WithSpread(BaseToolModule):
    """Override declared before the commons spread wins first-match."""

  assert WithSpread.info.params == [override, *commons]
  assert WithSpread.info.param("max_tokens").default == 4000


def test_duplicate_scalar_kwarg_then_modifier_raises():
  with pytest.raises(ValueError, match="duplicate assignment of 'name'"):
    @tool.name("other")
    @tool(name="calc")
    class DupKwargThenModifier(BaseToolModule):
      """Dup."""


def test_duplicate_scalar_modifier_then_kwarg_raises():
  with pytest.raises(ValueError, match="duplicate assignment of 'name'"):
    @tool(name="calc")
    @tool.name("other")
    class DupModifierThenKwarg(BaseToolModule):
      """Dup."""


def test_duplicate_scalar_two_modifiers_raises():
  with pytest.raises(ValueError, match="duplicate assignment of 'name'"):
    @tool
    @tool.name("a")
    @tool.name("b")
    class DupTwoModifiers(BaseToolModule):
      """Dup."""


def test_copy_on_write_leaves_parent_info_unchanged():
  @tool(name="parent", title="Parent", description="P")
  class ParentModule(BaseToolModule):
    """Parent."""

  parent_info = ParentModule.info
  parent_params = list(parent_info.params)

  @tool.title("Child Title")
  class ChildModule(ParentModule):
    pass

  assert ParentModule.info is parent_info
  assert ParentModule.info.title == "Parent"
  assert ParentModule.info.params == parent_params
  assert ChildModule.info is not ParentModule.info
  assert ChildModule.info.title == "Child Title"
  assert ChildModule.info.name == "parent"
  assert ChildModule.info.description == "P"


def test_copy_on_write_param_does_not_mutate_parent_params():
  @tool(name="parent_params")
  class ParentParams(BaseToolModule):
    """Parent."""

  spec = ParamSpec(name="extra", type=int)

  @tool.param(spec)
  class ChildParams(ParentParams):
    pass

  assert ParentParams.info.params == []
  assert ChildParams.info.params == [spec]


def test_protocol_kind_records_protocol_info():
  @protocol(name="probe")
  class ProbeProtocol:
    """A probe protocol."""

  assert isinstance(ProbeProtocol.info, ProtocolInfo)
  assert ProbeProtocol.info.name == "probe"
  assert ("claia.tool_protocols", ProbeProtocol) in iter_decorated_plugins()


def test_record_plugin_is_idempotent_by_identity():
  @tool(name="once")
  class OnceModule(BaseToolModule):
    """Once."""

  before = list(iter_decorated_plugins())
  record_plugin("claia.tool_modules", OnceModule)
  assert list(iter_decorated_plugins()) == before


########################################################################
#                         FUNCTION TOOL INFERENCE                      #
########################################################################
def test_function_tool_inference_types_annotated_and_defaults():
  @tool
  def add(
    a: Annotated[float, "First number to add"],
    b: Annotated[float, "Second number to add"],
    round_to: int = 2,
    items: list = None,
    flag: bool = False,
    label: str = "sum",
  ):
    """Add two numbers together."""
    return a + b

  defn = add.__claia_tool__
  assert add.__claia_tool__ is defn
  assert add(1.0, 2.0) == 3.0
  assert defn.name == "add"
  assert defn.description == "Add two numbers together."
  assert defn.callable is add

  assert defn.arguments["a"].data_type == "float"
  assert defn.arguments["a"].description == "First number to add"
  assert defn.arguments["a"].required is True
  assert defn.arguments["a"].default_value is None

  assert defn.arguments["b"].data_type == "float"
  assert defn.arguments["b"].description == "Second number to add"
  assert defn.arguments["b"].required is True

  assert defn.arguments["round_to"].data_type == "int"
  assert defn.arguments["round_to"].description == ""
  assert defn.arguments["round_to"].required is False
  assert defn.arguments["round_to"].default_value == 2

  assert defn.arguments["items"].data_type == "custom"
  assert defn.arguments["items"].required is False
  assert defn.arguments["items"].default_value is None

  assert defn.arguments["flag"].data_type == "bool"
  assert defn.arguments["label"].data_type == "str"
  assert "self" not in defn.arguments
  assert "kwargs" not in defn.arguments


def test_function_tool_skips_self_and_varargs():
  @tool
  def wrapped(self, cls, *args, extra: str, **kwargs):
    """Uses ignored args."""
    return extra

  defn = wrapped.__claia_tool__
  assert list(defn.arguments) == ["extra"]
  assert defn.arguments["extra"].data_type == "str"
  assert defn.arguments["extra"].required is True


def test_function_stacked_orders_converge():
  @tool
  @tool.description("Renamed add")
  @tool.name("sum")
  def order_mod_first(a: int, b: int):
    """Ignored."""
    return a + b

  @tool.description("Renamed add")
  @tool.name("sum")
  @tool
  def order_main_first(a: int, b: int):
    """Ignored."""
    return a + b

  a = order_mod_first.__claia_tool__
  b = order_main_first.__claia_tool__
  assert a.name == b.name == "sum"
  assert a.description == b.description == "Renamed add"
  assert a.arguments["a"].data_type == "int"
  assert b.arguments["a"].data_type == "int"


def test_function_title_modifier_raises():
  with pytest.raises(ValueError, match=r"\.title cannot be applied to a function"):
    @tool.title("Nope")
    def forbidden_title():
      """Nope."""


def test_function_param_modifier_raises():
  with pytest.raises(ValueError, match=r"\.param cannot be applied to a function"):
    @tool.param(ParamSpec(name="x"))
    def forbidden_param():
      """Nope."""


def test_protocol_decorator_rejects_functions():
  with pytest.raises(TypeError, match="cannot be applied to a function"):
    @protocol
    def not_a_protocol():
      """Nope."""


########################################################################
#                         DEFAULT GET_MODULE_TOOLS                     #
########################################################################
def test_default_get_module_tools_returns_bound_callables():
  @tool(name="mod")
  class DecoratedMod(BaseToolModule):
    """A decorated module."""

    @tool
    def ping(self) -> str:
      """Ping."""
      return "pong"

    @tool
    def echo(self, message: Annotated[str, "Message to echo"]) -> str:
      """Echo."""
      return message

  inst = DecoratedMod()
  tools = inst.get_module_tools()
  assert set(tools) == {"ping", "echo"}
  assert tools["ping"].description == "Ping."
  assert tools["echo"].arguments["message"].description == "Message to echo"
  assert tools["ping"].callable() == "pong"
  assert tools["echo"].callable("hi") == "hi"
  assert tools["ping"].callable.__self__ is inst
  assert tools["echo"].callable.__self__ is inst


def test_default_get_module_tools_empty_without_decorated_methods():
  @tool
  class EmptyMod(BaseToolModule):
    """Empty."""

  assert EmptyMod().get_module_tools() == {}


def test_sample_module_uses_decorators_and_preserves_catalog():
  plugin = SampleToolModule()
  assert SampleToolModule.info.name == "sample"
  assert SampleToolModule.info.title == "Sample Utilities"
  tools = plugin.get_module_tools()
  assert set(tools) == {"current_time", "add", "subtract", "echo"}

  assert tools["current_time"].description == "Get the current UTC time in ISO format"
  assert tools["add"].description == "Add two numbers together"
  assert tools["add"].arguments["a"].description == "First number to add"
  assert tools["add"].arguments["b"].description == "Second number to add"
  assert tools["add"].arguments["a"].data_type == "float"
  assert tools["add"].arguments["a"].required is True
  assert tools["subtract"].arguments["a"].description == "Number to subtract from"
  assert tools["subtract"].arguments["b"].description == "Number to subtract"
  assert tools["echo"].arguments["message"].description == "Message to echo back"
  assert tools["echo"].arguments["message"].data_type == "str"

  assert tools["add"].callable.__self__ is plugin
  assert "3.0 + 4.0 = 7.0" in tools["add"].callable(3.0, 4.0)
  assert tools["echo"].callable("hi") == "hi"


def test_system_module_uses_decorators():
  plugin = SystemToolModule()
  assert SystemToolModule.info.name == "system"
  assert SystemToolModule.info.title == "System Utilities"
  tools = plugin.get_module_tools()
  assert set(tools) == {"exit"}
  assert tools["exit"].description == "Exit the application"
  assert tools["exit"].callable.__self__ is plugin
  assert PENDING_ATTR not in SystemToolModule.__dict__


def test_definitions_decorator_records_class():
  from claia.core.decorators import definitions

  @definitions
  class ProbeDefinitions:
    """Probe provider."""

    def get_definitions(self):
      return {}

  assert ("claia.definitions", ProbeDefinitions) in iter_decorated_plugins()
  assert ProbeDefinitions.info.name == "probe_definitions"
  assert ProbeDefinitions.info.title == "Probe Definitions"
  assert ProbeDefinitions.info.description == "Probe provider."

  with pytest.raises(TypeError, match="cannot be applied to a function"):
    definitions(lambda: None)
