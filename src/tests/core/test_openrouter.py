"""
Tests for the OpenRouter API architecture and definitions.
"""

from claia.core.data import Conversation
from claia.core.definitions.anthropic import AnthropicDefinitions
from claia.core.definitions.deepseek import DeepSeekDefinitions
from claia.core.definitions.meta import MetaDefinitions
from claia.core.definitions.moonshot import MoonshotDefinitions
from claia.core.definitions.openai import OpenAIDefinitions
from claia.core.definitions.qwen import QwenDefinitions
from claia.core.definitions.zai import ZaiDefinitions
from claia.core.enums.conversation import MessageRole
from claia.core.data.chunks import TextChunk
from claia.core.enums.data import ArtifactType
from claia.core.models.api.openrouter import OpenRouterModel


class FakeResponse:
  def __init__(self, json_data=None, lines=None):
    self._json_data = json_data or {}
    self._lines = lines or []

  def json(self):
    return self._json_data

  def iter_lines(self):
    return iter(self._lines)


class RecordingOpenRouterModel(OpenRouterModel):
  def __init__(self, *args, response, **kwargs):
    super().__init__(*args, **kwargs)
    self.response = response
    self.calls = []

  def post(self, endpoint, data, *args, **kwargs):
    self.calls.append((endpoint, data, kwargs))
    return self.response


def _sequence(conversation, system=None):
  from claia.core.deployments.dummy import DummyDeployment
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.data.models.conversation.message_sequence import MessageSequence
  from claia.core.enums.data import ArtifactType
  return DummyDeployment().translate(
    conversation,
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
  model = RecordingOpenRouterModel(
    "openai/gpt-4o-mini",
    openrouter_api_token="secret",
    response=response,
  )

  chunks = list(model.generate(
    _sequence(_conversation(), system="Be brief"),
    stream=False,
    max_tokens=25,
    temperature=0,
    top_p=1,
    top_k=None,
  ))

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
  assert model.session.headers["Authorization"] == "Bearer secret"


def test_openrouter_model_streams_deltas():
  response = FakeResponse(lines=[
    b'data: {"choices":[{"delta":{"content":"Hello "}}]}',
    b'data: {"choices":[{"delta":{"content":"world"}}]}',
    b"data: [DONE]",
  ])
  model = RecordingOpenRouterModel("anthropic/claude-sonnet-4.5", response=response)

  chunks = list(model.generate(
    _sequence(_conversation(), system="Be brief"),
    stream=True,
    max_tokens=25,
  ))

  endpoint, data, request_kwargs = model.calls[0]
  assert [c.data for c in chunks] == ["Hello ", "world"]
  assert endpoint == "chat/completions"
  assert data["stream"] is True
  assert request_kwargs == {"stream": True}


def test_openrouter_model_surfaces_api_errors():
  response = FakeResponse({
    "error": {"code": "invalid_model", "message": "Unknown model"},
  })
  model = RecordingOpenRouterModel("bad/model", response=response)

  chunks = list(model.generate(_sequence(_conversation()), stream=False))

  assert [c.data for c in chunks] == ["OpenRouter error (invalid_model): Unknown model"]


def test_openrouter_architecture_exposes_model_and_params():
  info = OpenRouterModel.info

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

  assert "openrouter-gpt-4o-mini" not in MoonshotDefinitions().get_definitions()
  assert kimi.architectures == ["openrouter"]
  assert kimi.deployments == ["api"]
  assert kimi.identifiers == {"openrouter": "moonshotai/kimi-k3"}
  assert deepseek.identifiers == {"openrouter": "deepseek/deepseek-v4-pro"}
  assert glm.identifiers == {"openrouter": "z-ai/glm-5.3"}
  assert qwen36.context_length == 1000000
  assert ArtifactType.IMAGE in qwen36.inputs
  assert qwen35.identifiers == {"openrouter": "qwen/qwen3.5-397b-a17b"}
  assert llama.context_length == 1000000
  assert ArtifactType.IMAGE in kimi.inputs
  assert ArtifactType.IMAGE in qwen35.inputs
  assert kimi.outputs == [TextChunk]
  assert qwen35.outputs == [TextChunk]
