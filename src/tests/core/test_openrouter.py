"""
Tests for the OpenRouter API architecture and definitions.
"""

import pytest

from claia.core.data import AgentRequest, Conversation
from claia.core.definitions.anthropic import AnthropicDefinitions
from claia.core.definitions.deepseek import DeepSeekDefinitions
from claia.core.definitions.meta import MetaDefinitions
from claia.core.definitions.moonshot import MoonshotDefinitions
from claia.core.definitions.openai import OpenAIDefinitions
from claia.core.definitions.qwen import QwenDefinitions
from claia.core.definitions.zai import ZaiDefinitions
from claia.core.enums.conversation import MessageRole
from claia.core.data.chunks import TextChunk, ToolChunk
from claia.core.enums.data import ArtifactType
from claia.core.architectures.api.openrouter import OpenRouterArchitecture
from claia.core.results import DeploymentError


class FakeResponse:
  def __init__(self, json_data=None, lines=None):
    self._json_data = json_data or {}
    self._lines = lines or []

  def json(self):
    return self._json_data

  def iter_lines(self):
    return iter(self._lines)


class RecordingOpenRouterArchitecture(OpenRouterArchitecture):
  def __init__(self, *args, response, **kwargs):
    super().__init__(*args, **kwargs)
    self.response = response
    self.calls = []

  def post(self, endpoint, data, *args, **kwargs):
    self.calls.append((endpoint, data, kwargs))
    return self.response


def _request(inputs, **args):
  return AgentRequest(
    model="test",
    provider_model="test",
    architecture_class=object,
    deployment=None,
    inputs=inputs,
    args=args,
  )


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


def test_openrouter_model_builds_non_streaming_request():
  response = FakeResponse({
    "choices": [{"message": {"content": "Hi there"}}],
  })
  model = RecordingOpenRouterArchitecture(
    "openai/gpt-4o-mini",
    openrouter_api_token="secret",
    response=response,
  )

  chunks = list(model.generate(_request(
    _sequence(_conversation(), system="Be brief"),
    stream=False,
    max_tokens=25,
    temperature=0,
    top_p=1,
    top_k=None,
  )))

  endpoint, data, request_kwargs = model.calls[0]
  assert [c.data for c in chunks] == ["Hi there"]
  assert endpoint == "chat/completions"
  assert request_kwargs == {}
  assert data["model"] == "openai/gpt-4o-mini"
  assert data["temperature"] == 0
  assert "top_k" not in data
  assert data["messages"] == [
    {"role": "system", "content": "Be brief"},
    {"role": "user", "content": "Hello"},
  ]
  assert "tools" not in data
  assert model.session.headers["Authorization"] == "Bearer secret"


def test_openrouter_model_streams_deltas():
  response = FakeResponse(lines=[
    b'data: {"choices":[{"delta":{"content":"Hello "}}]}',
    b'data: {"choices":[{"delta":{"content":"world"}}]}',
    b"data: [DONE]",
  ])
  model = RecordingOpenRouterArchitecture("anthropic/claude-sonnet-4.5", response=response)

  chunks = list(model.generate(_request(
    _sequence(_conversation(), system="Be brief"),
    stream=True,
    max_tokens=25,
  )))

  endpoint, data, request_kwargs = model.calls[0]
  assert [c.data for c in chunks if isinstance(c, TextChunk)] == ["Hello ", "world"]
  assert endpoint == "chat/completions"
  assert data["stream"] is True
  assert data["stream_options"] == {"include_usage": True}
  assert request_kwargs == {"stream": True}


def test_openrouter_model_raises_on_api_errors():
  response = FakeResponse({
    "error": {"code": "invalid_model", "message": "Unknown model"},
  })
  model = RecordingOpenRouterArchitecture("bad/model", response=response)

  with pytest.raises(DeploymentError, match=r"OpenRouter error \(invalid_model\): Unknown model"):
    list(model.generate(_request(_sequence(_conversation()), stream=False)))


def _echo_ref():
  from claia.core.plugins.base import ArgumentDefinition, ToolReference
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


def test_openrouter_sends_chat_tools_and_yields_tool_chunk():
  response = FakeResponse({
    "choices": [{
      "message": {
        "content": "",
        "tool_calls": [{
          "id": "call_1",
          "type": "function",
          "function": {
            "name": "demo.echo",
            "arguments": '{"message": "hi"}',
          },
        }],
      },
    }],
  })
  model = RecordingOpenRouterArchitecture("openai/gpt-4o-mini", response=response)

  chunks = list(model.generate(_request(
    _sequence(_conversation()),
    stream=False,
    tools=[_echo_ref()],
  )))

  endpoint, data, _ = model.calls[0]
  assert endpoint == "chat/completions"
  assert data["tools"][0]["function"]["name"] == "demo__echo"
  assert len(chunks) == 1
  assert isinstance(chunks[0], ToolChunk)
  assert chunks[0].tool_name == "demo.echo"
  assert chunks[0].payload == {"message": "hi"}
  assert chunks[0].call_id == "call_1"


def test_openrouter_streams_tool_call_deltas():
  response = FakeResponse(lines=[
    b'data: {"choices":[{"delta":{"content":"Let me "}}]}',
    b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"demo.echo","arguments":""}}]}}]}',
    b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"message\\": \\"hi\\"}"}}]}}]}',
    b"data: [DONE]",
  ])
  model = RecordingOpenRouterArchitecture("openai/gpt-4o-mini", response=response)

  chunks = list(model.generate(_request(
    _sequence(_conversation()),
    stream=True,
    tools=[_echo_ref()],
  )))

  assert [c.data for c in chunks if isinstance(c, TextChunk)] == ["Let me "]
  tool = next(c for c in chunks if isinstance(c, ToolChunk))
  assert tool.tool_name == "demo.echo"
  assert tool.payload == {"message": "hi"}
  assert tool.call_id == "call_1"


def _sequence_with_utility():
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
  return MessageSequence(messages=[
    Message(role=MessageRole.USER, content="Hello"),
    Message(role=MessageRole.ASSISTANT, content="calling"),
    utility,
  ])


def test_openrouter_without_tools_keeps_manual_utility_text():
  from claia.core.data.artifacts import ToolArtifact
  response = FakeResponse({"choices": [{"message": {"content": "done"}}]})
  model = RecordingOpenRouterArchitecture("openai/gpt-4o-mini", response=response)

  list(model.generate(_request(_sequence_with_utility(), stream=False)))

  messages = model.calls[0][1]["messages"]
  assert messages[2]["role"] == "user"
  assert messages[2]["content"] == ToolArtifact.format_result("demo.echo", "pong")
  assert "tools" not in model.calls[0][1]


def test_openrouter_native_follow_up_uses_tool_role():
  response = FakeResponse({"choices": [{"message": {"content": "done"}}]})
  model = RecordingOpenRouterArchitecture("openai/gpt-4o-mini", response=response)

  list(model.generate(_request(_sequence_with_utility(), stream=False, tools=[_echo_ref()])))

  messages = model.calls[0][1]["messages"]
  assert messages[1]["tool_calls"][0]["id"] == "call_1"
  assert messages[2]["role"] == "tool"
  assert messages[2]["content"] == "pong"


def test_openrouter_architecture_exposes_model_and_params():
  info = OpenRouterArchitecture.info

  assert info.name == "openrouter"
  assert info.param("openrouter_api_token") is not None
  assert info.param("stream").default is True


def test_native_provider_definitions_include_openrouter_endpoint():
  gpt = OpenAIDefinitions().get_definitions()["gpt-5.6-sol"]
  openai = OpenAIDefinitions().get_definitions()["gpt-4o-mini"]
  anthropic = AnthropicDefinitions().get_definitions()["claude-sonnet-5"]

  assert gpt.aliases == ["gpt", "gpt-5.6"]
  assert gpt.identifiers == {"openai": "gpt-5.6-sol", "openrouter": "openai/gpt-5.6-sol"}
  assert openai.architectures == ["openai", "openrouter"]
  assert openai.identifiers["openrouter"] == "openai/gpt-4o-mini"
  assert anthropic.architectures == ["anthropic", "openrouter"]
  assert anthropic.identifiers["openrouter"] == "anthropic/claude-sonnet-5"


def test_openrouter_company_definitions_are_large_open_models():
  kimi = MoonshotDefinitions().get_definitions()["kimi-k3"]
  deepseek = DeepSeekDefinitions().get_definitions()["deepseek-v4-pro"]
  glm = ZaiDefinitions().get_definitions()["glm-5.3"]
  qwen36 = QwenDefinitions().get_definitions()["qwen3.6-plus"]
  qwen35 = QwenDefinitions().get_definitions()["qwen3.5-397b-a17b"]
  llama = MetaDefinitions().get_definitions()["llama-4-maverick"]
  llama_scout = MetaDefinitions().get_definitions()["llama-4-scout"]

  assert "openrouter-gpt-4o-mini" not in MoonshotDefinitions().get_definitions()
  assert kimi.architectures == ["openrouter"]
  assert kimi.identifiers == {"openrouter": "moonshotai/kimi-k3"}
  assert deepseek.identifiers == {"openrouter": "deepseek/deepseek-v4-pro"}
  assert glm.identifiers == {"openrouter": "z-ai/glm-5.3"}
  assert qwen36.context_length == 1000000
  assert ArtifactType.IMAGE in qwen36.inputs
  assert qwen35.identifiers == {"openrouter": "qwen/qwen3.5-397b-a17b"}
  assert llama.context_length == 1000000
  assert ArtifactType.IMAGE in kimi.inputs
  assert ArtifactType.IMAGE in qwen35.inputs
  assert kimi.outputs == [TextChunk, ToolChunk]
  assert qwen35.outputs == [TextChunk, ToolChunk]
  assert llama.outputs == [TextChunk, ToolChunk]
  assert llama_scout.outputs == [TextChunk]
