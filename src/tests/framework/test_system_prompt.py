"""Tests for agent system-prompt composition and SimpleAgent wiring."""

from claia.core.data.chunks import TextChunk
from claia.core.enums.parser import TagType
from claia.core.enums.task import TaskStatus
from claia.core.parser.defaults import DEFAULT_TAGS
from claia.core.parser.types import TagSpec
from claia.core.plugins.base import ArgumentDefinition, ToolReference
from claia.framework.agents.simple import SimpleAgent
from claia.framework.agents.system import (
  DEFAULT_SYSTEM_PROMPT,
  compose_system_prompt,
  format_tool_result,
  render_tool_instructions,
)


def _echo_tool() -> ToolReference:
  return ToolReference(
    qualified_name="sample.echo",
    description="Echo back the provided message",
    protocol_name="simple",
    parameter_schema={
      "message": ArgumentDefinition(
        name="message",
        description="Message to echo back",
        data_type="str",
        required=True,
      ),
      "registry": ArgumentDefinition(
        name="registry",
        description="injected",
        data_type="custom",
        required=False,
      ),
    },
  )


def test_compose_without_tools_uses_default_persona():
  assert compose_system_prompt() == DEFAULT_SYSTEM_PROMPT
  assert compose_system_prompt("   ") == DEFAULT_SYSTEM_PROMPT


def test_compose_without_tools_keeps_caller_persona():
  assert compose_system_prompt("You write poetry.") == "You write poetry."


def test_compose_prepends_tool_instructions_to_persona():
  tools = [_echo_tool()]
  specs = list(DEFAULT_TAGS.values())
  composed = compose_system_prompt(
    "You write poetry.",
    tools=tools,
    tag_specs=specs,
  )
  assert composed.startswith("You can call tools")
  assert composed.endswith("You write poetry.")
  assert "[TOOL_CALL]" in composed
  assert "[/TOOL_CALL]" in composed
  assert "[TOOL_RESULT]" in composed
  assert "sample.echo" in composed
  assert "message (str, required): Message to echo back" in composed
  assert "registry" not in composed.split("Available tools:")[1]


def test_compose_with_tools_and_no_persona_uses_default():
  composed = compose_system_prompt(
    tools=[_echo_tool()],
    tag_specs=list(DEFAULT_TAGS.values()),
  )
  assert composed.endswith(DEFAULT_SYSTEM_PROMPT)


def test_format_tool_result_wraps_name_and_body():
  assert format_tool_result("demo.echo", "echoed:hi") == (
    '[TOOL_RESULT name="demo.echo"]\n'
    'echoed:hi\n'
    '[/TOOL_RESULT]'
  )
  assert format_tool_result("  ", "x") == (
    '[TOOL_RESULT name="unknown"]\n'
    'x\n'
    '[/TOOL_RESULT]'
  )


def test_render_skips_when_no_tool_tag_spec():
  assert render_tool_instructions([_echo_tool()], []) == ""


def test_render_json_schema_arguments():
  tool = ToolReference(
    qualified_name="mcp.fs.read",
    description="Read a file",
    protocol_name="mcp",
    parameter_schema={
      "type": "object",
      "required": ["path"],
      "properties": {
        "path": {"type": "string", "description": "File path"},
        "offset": {"type": "integer"},
      },
    },
  )
  text = render_tool_instructions([tool], list(DEFAULT_TAGS.values()))
  assert "mcp.fs.read: Read a file" in text
  assert "path (string, required): File path" in text
  assert "offset (integer, optional)" in text


def test_simple_agent_passes_composed_system_to_run(task):
  captured = {}

  class FakeRegistry:
    def get_supported_models(self):
      return {}

    def list_tools(self):
      return [_echo_tool()]

    def resolve_qualified_name(self, name):
      return name

    def run(self, model_id, conversation, streaming=False, system=None, **kwargs):
      captured["system"] = system
      assert streaming is True
      return iter([TextChunk(data="ok")])

  task.parameters["system"] = "Stay terse."
  updated = SimpleAgent.execute(task, registry=FakeRegistry())

  assert updated.status == TaskStatus.COMPLETED
  system = captured["system"]
  assert system.startswith("You can call tools")
  assert system.endswith("Stay terse.")
  assert "sample.echo" in system


def test_simple_agent_default_persona_when_system_omitted(task):
  captured = {}

  class FakeRegistry:
    def get_supported_models(self):
      return {}

    def list_tools(self):
      return []

    def resolve_qualified_name(self, name):
      return name

    def run(self, model_id, conversation, streaming=False, system=None, **kwargs):
      captured["system"] = system
      return iter([TextChunk(data="ok")])

  updated = SimpleAgent.execute(task, registry=FakeRegistry())

  assert updated.status == TaskStatus.COMPLETED
  assert captured["system"] == DEFAULT_SYSTEM_PROMPT


def test_simple_agent_uses_model_tag_override(task):
  captured = {}
  custom = TagSpec(
    tag_type=TagType.TOOL,
    open_token="<tool>",
    close_token="</tool>",
  )

  class FakeRegistry:
    def get_supported_models(self):
      class Def:
        tag_overrides = {TagType.TOOL: custom}
      return {"dummy-model": Def()}

    def list_tools(self):
      return [_echo_tool()]

    def resolve_qualified_name(self, name):
      return name

    def run(self, model_id, conversation, streaming=False, system=None, **kwargs):
      captured["system"] = system
      return iter([TextChunk(data="ok")])

  SimpleAgent.execute(task, registry=FakeRegistry())
  assert "<tool>" in captured["system"]
  assert "</tool>" in captured["system"]
  assert "[TOOL_CALL]" not in captured["system"]
