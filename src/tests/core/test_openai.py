"""Tests for the OpenAI Responses API architecture."""

from claia.core.architectures.api.openai import OpenAIArchitecture
from claia.core.data import Conversation
from claia.core.data.chunks import TextChunk, ToolChunk
from claia.core.enums.conversation import MessageRole
from claia.core.plugins.base import ArgumentDefinition, ToolReference
from claia.core.results import DeploymentError

import pytest


class FakeResponse:
  def __init__(self, json_data=None, lines=None):
    self._json_data = json_data or {}
    self._lines = lines or []

  def json(self):
    return self._json_data

  def iter_lines(self):
    return iter(self._lines)


class RecordingOpenAIArchitecture(OpenAIArchitecture):
  def __init__(self, *args, response, **kwargs):
    super().__init__(*args, **kwargs)
    self.response = response
    self.calls = []

  def post(self, endpoint, data, *args, **kwargs):
    self.calls.append((endpoint, data, kwargs))
    return self.response


def _sequence(conversation, system=None):
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.data.models.conversation.message_sequence import MessageSequence
  from claia.core.enums.data import ArtifactType
  return conversation.to_model_inputs(
    ModelDefinition(inputs=[ArtifactType.TEXT, MessageSequence]),
    system=system,
  )


def _conversation():
  conversation = Conversation(title="T")
  conversation.add_message(MessageRole.USER, "Hello")
  return conversation


def _echo_ref():
  return ToolReference(
    qualified_name="demo.echo",
    description="Echo",
    protocol_name="simple",
    parameter_schema={
      "message": ArgumentDefinition(
        name="message", description="Text", data_type="str", required=True,
      ),
    },
  )


def test_openai_blocking_text_omits_tools():
  response = FakeResponse({
    "output": [{
      "type": "message",
      "content": [{"type": "output_text", "text": "Hi there"}],
    }],
  })
  model = RecordingOpenAIArchitecture("gpt-4o-mini", openai_api_token="secret", response=response)

  chunks = list(model.generate(_sequence(_conversation(), system="Be brief"), stream=False))

  endpoint, data, _ = model.calls[0]
  assert [c.data for c in chunks] == ["Hi there"]
  assert endpoint == "responses"
  assert data["model"] == "gpt-4o-mini"
  assert data["instructions"] == "Be brief"
  assert "tools" not in data
  assert model.session.headers["Authorization"] == "Bearer secret"


def test_openai_sends_responses_tools_and_yields_function_call():
  response = FakeResponse({
    "output": [{
      "type": "function_call",
      "call_id": "call_1",
      "name": "demo.echo",
      "arguments": '{"message": "hi"}',
    }],
  })
  model = RecordingOpenAIArchitecture("gpt-4o-mini", response=response)

  chunks = list(model.generate(
    _sequence(_conversation()),
    stream=False,
    tools=[_echo_ref()],
  ))

  _, data, _ = model.calls[0]
  assert data["tools"][0]["name"] == "demo.echo"
  assert data["tools"][0]["type"] == "function"
  assert len(chunks) == 1
  assert isinstance(chunks[0], ToolChunk)
  assert chunks[0].tool_name == "demo.echo"
  assert chunks[0].payload == {"message": "hi"}
  assert chunks[0].call_id == "call_1"


def test_openai_streams_text_and_function_call():
  response = FakeResponse(lines=[
    b'data: {"type":"response.output_text.delta","delta":"Let me "}',
    b'data: {"type":"response.output_item.done","item":{"type":"function_call","call_id":"call_1","name":"demo.echo","arguments":"{\\"message\\":\\"hi\\"}"}}',
    b'data: {"type":"response.completed","response":{"usage":{"output_tokens":4}}}',
  ])
  model = RecordingOpenAIArchitecture("gpt-4o-mini", response=response)

  chunks = list(model.generate(
    _sequence(_conversation()),
    stream=True,
    tools=[_echo_ref()],
  ))

  assert [c.data for c in chunks if isinstance(c, TextChunk)] == ["Let me "]
  tool = next(c for c in chunks if isinstance(c, ToolChunk))
  assert tool.tool_name == "demo.echo"
  assert tool.payload == {"message": "hi"}
  assert tool.call_id == "call_1"


def test_openai_completed_event_emits_function_call_once():
  response = FakeResponse(lines=[
    b'data: {"type":"response.output_item.done","item":{"type":"function_call","call_id":"call_1","name":"demo.echo","arguments":"{\\"message\\":\\"hi\\"}"}}',
    b'data: {"type":"response.completed","response":{"output":[{"type":"function_call","call_id":"call_1","name":"demo.echo","arguments":"{\\"message\\":\\"hi\\"}"}]}}',
  ])
  model = RecordingOpenAIArchitecture("gpt-4o-mini", response=response)

  chunks = list(model.generate(_sequence(_conversation()), stream=True, tools=[_echo_ref()]))
  tools = [c for c in chunks if isinstance(c, ToolChunk)]
  assert len(tools) == 1


def test_openai_native_follow_up_uses_function_call_items():
  import json
  from claia.core.data import Message, MessageSequence
  from claia.core.data.artifacts import ToolArtifact
  from claia.core.enums.parser import TagType

  utility = Message(
    role=MessageRole.UTILITY,
    tag_type=TagType.TOOL,
    content=json.dumps({"name": "demo.echo", "parameters": {"message": "hi"}}),
  )
  utility.add_artifact(ToolArtifact.from_result("demo.echo", "pong", call_id="call_1"))
  sequence = MessageSequence(messages=[
    Message(role=MessageRole.USER, content="Hello"),
    Message(role=MessageRole.ASSISTANT, content="calling"),
    utility,
  ])
  response = FakeResponse({
    "output": [{"type": "message", "content": [{"type": "output_text", "text": "done"}]}],
  })
  model = RecordingOpenAIArchitecture("gpt-4o-mini", response=response)

  list(model.generate(sequence, stream=False, tools=[_echo_ref()]))

  items = model.calls[0][1]["input"]
  assert items[2]["type"] == "function_call"
  assert items[2]["call_id"] == "call_1"
  assert items[3] == {
    "type": "function_call_output",
    "call_id": "call_1",
    "output": "pong",
  }


def test_openai_raises_on_api_errors():
  response = FakeResponse({"error": {"code": "invalid_model", "message": "Unknown model"}})
  model = RecordingOpenAIArchitecture("bad-model", response=response)

  with pytest.raises(DeploymentError, match=r"OpenAI error \(invalid_model\): Unknown model"):
    list(model.generate(_sequence(_conversation()), stream=False))
