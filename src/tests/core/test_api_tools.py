"""Shared native tool-calling helpers for API architectures."""

import json

from claia.core.architectures.api.tools import (
  anthropic_tools,
  format_anthropic_messages,
  format_openai_chat_messages,
  format_openai_responses_input,
  json_schema_from_tool,
  openai_chat_tools,
  openai_responses_tools,
  parse_arguments,
  resolve_wire_tool_name,
  tool_chunk,
  wire_tool_name,
)
from claia.core.data import Message, MessageSequence
from claia.core.data.artifacts import ToolArtifact
from claia.core.enums.conversation import MessageRole
from claia.core.enums.parser import TagType
from claia.core.plugins.base import ArgumentDefinition, ToolReference


def _echo_ref() -> ToolReference:
  return ToolReference(
    qualified_name="demo.echo",
    description="Echo a message",
    protocol_name="simple",
    parameter_schema={
      "message": ArgumentDefinition(
        name="message",
        description="Text to echo",
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


def _utility(name: str, args: dict, result: str, call_id: str = "call_1") -> Message:
  message = Message(
    role=MessageRole.UTILITY,
    tag_type=TagType.TOOL,
    content=json.dumps({"name": name, "parameters": args}),
  )
  message.add_artifact(ToolArtifact.from_result(name, result, call_id=call_id))
  return message


def _sequence_with_call() -> MessageSequence:
  return MessageSequence(messages=[
    Message(role=MessageRole.USER, content="hi"),
    Message(role=MessageRole.ASSISTANT, content="calling"),
    _utility("demo.echo", {"message": "yo"}, "pong", call_id="call_echo"),
    Message(role=MessageRole.ASSISTANT, content="done"),
  ])


def test_json_schema_from_argument_map_strips_injectables():
  schema = json_schema_from_tool(_echo_ref())
  assert schema == {
    "type": "object",
    "properties": {
      "message": {"type": "string", "description": "Text to echo"},
    },
    "required": ["message"],
  }


def test_json_schema_passes_through_json_schema_dict():
  ref = ToolReference(
    qualified_name="mcp.search",
    description="Search",
    protocol_name="mcp",
    parameter_schema={
      "type": "object",
      "properties": {
        "q": {"type": "string"},
        "registry": {"type": "object"},
      },
      "required": ["q", "registry"],
    },
  )
  schema = json_schema_from_tool(ref)
  assert schema["properties"] == {"q": {"type": "string"}}
  assert schema["required"] == ["q"]


def test_wire_tool_name_encodes_dotted_namespaces():
  assert wire_tool_name("cli.settings_get") == "cli__settings_get"
  assert wire_tool_name("mcp.fs.read") == "mcp__fs__read"
  assert resolve_wire_tool_name("cli__settings_get") == "cli.settings_get"
  assert resolve_wire_tool_name("demo__echo", [_echo_ref()]) == "demo.echo"


def test_provider_tool_arrays():
  refs = [_echo_ref()]
  assert openai_responses_tools(refs) == [{
    "type": "function",
    "name": "demo__echo",
    "description": "Echo a message",
    "parameters": json_schema_from_tool(refs[0]),
  }]
  assert openai_chat_tools(refs)[0]["function"]["name"] == "demo__echo"
  assert anthropic_tools(refs)[0]["name"] == "demo__echo"
  assert anthropic_tools(refs)[0]["input_schema"]["required"] == ["message"]


def test_parse_arguments_and_tool_chunk():
  assert parse_arguments('{"city": "SF"}') == {"city": "SF"}
  assert parse_arguments({"city": "SF"}) == {"city": "SF"}
  assert parse_arguments("not-json") == {}
  chunk = tool_chunk("demo.echo", '{"message": "hi"}', "call_1")
  assert chunk.tool_name == "demo.echo"
  assert chunk.payload == {"message": "hi"}
  assert chunk.call_id == "call_1"


def test_openai_responses_follow_up_uses_function_call_items():
  items = format_openai_responses_input(_sequence_with_call())
  assert items == [
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "calling"},
    {
      "type": "function_call",
      "call_id": "call_echo",
      "name": "demo__echo",
      "arguments": '{"message": "yo"}',
    },
    {
      "type": "function_call_output",
      "call_id": "call_echo",
      "output": "pong",
    },
    {"role": "assistant", "content": "done"},
  ]


def test_openai_chat_follow_up_attaches_tool_calls_to_assistant():
  messages = format_openai_chat_messages(_sequence_with_call())
  assert messages[1]["role"] == "assistant"
  assert messages[1]["tool_calls"] == [{
    "id": "call_echo",
    "type": "function",
    "function": {"name": "demo__echo", "arguments": '{"message": "yo"}'},
  }]
  assert messages[2] == {
    "role": "tool",
    "tool_call_id": "call_echo",
    "content": "pong",
  }


def test_openai_chat_two_utilities_share_one_assistant():
  sequence = MessageSequence(messages=[
    Message(role=MessageRole.USER, content="hi"),
    Message(role=MessageRole.ASSISTANT, content="calling"),
    _utility("demo.echo", {"message": "a"}, "A", call_id="c1"),
    _utility("demo.echo", {"message": "b"}, "B", call_id="c2"),
  ])
  messages = format_openai_chat_messages(sequence)
  assert [m["role"] for m in messages] == ["user", "assistant", "tool", "tool"]
  assert len(messages[1]["tool_calls"]) == 2


def test_anthropic_follow_up_uses_tool_use_and_tool_result():
  messages = format_anthropic_messages(_sequence_with_call())
  assert messages[1]["role"] == "assistant"
  assert messages[1]["content"][0] == {"type": "text", "text": "calling"}
  assert messages[1]["content"][1] == {
    "type": "tool_use",
    "id": "call_echo",
    "name": "demo__echo",
    "input": {"message": "yo"},
  }
  assert messages[2] == {
    "role": "user",
    "content": [{
      "type": "tool_result",
      "tool_use_id": "call_echo",
      "content": "pong",
    }],
  }


def test_anthropic_two_utilities_merge_into_one_user_result():
  sequence = MessageSequence(messages=[
    Message(role=MessageRole.USER, content="hi"),
    Message(role=MessageRole.ASSISTANT, content="calling"),
    _utility("demo.echo", {"message": "a"}, "A", call_id="c1"),
    _utility("demo.echo", {"message": "b"}, "B", call_id="c2"),
  ])
  messages = format_anthropic_messages(sequence)
  assert [m["role"] for m in messages] == ["user", "assistant", "user"]
  assert [b["type"] for b in messages[1]["content"]] == ["text", "tool_use", "tool_use"]
  assert [b["tool_use_id"] for b in messages[2]["content"]] == ["c1", "c2"]
