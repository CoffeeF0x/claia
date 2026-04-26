"""
Tests for the OpenRouter API architecture and definitions.
"""

from claia.core.architectures.openrouter import OpenRouterPlugin
from claia.core.data import Conversation
from claia.core.definitions.anthropic import AnthropicDefinitionsPlugin
from claia.core.definitions.openai import OpenAIDefinitionsPlugin
from claia.core.definitions.openrouter import OpenRouterDefinitionsPlugin
from claia.core.enums.conversation import MessageRole
from claia.core.models.api.openrouter import OpenRouterModel
from claia.core.modality import Modality


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


def _conversation():
  conversation = Conversation(title="T", prompt={"system": "Be brief"})
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
    _conversation(),
    stream=False,
    max_tokens=25,
    temperature=0,
    top_p=1,
    top_k=None,
  ))

  endpoint, data, request_kwargs = model.calls[0]
  assert chunks == ["Hi there"]
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

  chunks = list(model.generate(_conversation(), stream=True, max_tokens=25))

  endpoint, data, request_kwargs = model.calls[0]
  assert chunks == ["Hello ", "world"]
  assert endpoint == "chat/completions"
  assert data["stream"] is True
  assert request_kwargs == {"stream": True}


def test_openrouter_model_surfaces_api_errors():
  response = FakeResponse({
    "error": {"code": "invalid_model", "message": "Unknown model"},
  })
  model = RecordingOpenRouterModel("bad/model", response=response)

  chunks = list(model.generate(_conversation(), stream=False))

  assert chunks == ["OpenRouter error (invalid_model): Unknown model"]


def test_openrouter_architecture_exposes_model_and_params():
  info = OpenRouterPlugin().get_architecture_info()

  assert OpenRouterPlugin().get_model_class() is OpenRouterModel
  assert info.name == "openrouter"
  assert info.param("openrouter_api_token") is not None
  assert info.param("stream").default is True


def test_native_provider_definitions_include_openrouter_endpoint():
  gpt = OpenAIDefinitionsPlugin().get_definitions()["gpt-5.5"]
  openai = OpenAIDefinitionsPlugin().get_definitions()["gpt-4o-mini"]
  anthropic = AnthropicDefinitionsPlugin().get_definitions()["claude-sonnet-4-6"]

  assert gpt.aliases == ["gpt"]
  assert gpt.identifiers == {"openai": "gpt-5.5", "openrouter": "openai/gpt-5.5"}
  assert openai.architectures == ["openai", "openrouter"]
  assert openai.identifiers["openrouter"] == "openai/gpt-4o-mini"
  assert anthropic.architectures == ["anthropic", "openrouter"]
  assert anthropic.identifiers["openrouter"] == "anthropic/claude-sonnet-4.6"


def test_openrouter_definitions_are_large_open_models():
  definitions = OpenRouterDefinitionsPlugin().get_definitions()
  kimi = definitions["kimi-k2.6"]
  deepseek = definitions["deepseek-v4-pro"]
  glm = definitions["glm-5.1"]
  qwen36 = definitions["qwen3.6-plus"]
  qwen35 = definitions["qwen3.5-397b-a17b"]
  llama = definitions["llama-4-maverick"]

  assert "openrouter-gpt-4o-mini" not in definitions
  assert kimi.architectures == ["openrouter"]
  assert kimi.deployments == ["api"]
  assert kimi.identifiers == {"openrouter": "moonshotai/kimi-k2.6"}
  assert deepseek.identifiers == {"openrouter": "deepseek/deepseek-v4-pro"}
  assert glm.identifiers == {"openrouter": "z-ai/glm-5.1"}
  assert qwen36.context_length == 1000000
  assert qwen35.identifiers == {"openrouter": "qwen/qwen3.5-397b-a17b"}
  assert llama.context_length == 1000000
  assert Modality.IMAGE in kimi.input_modalities
  assert Modality.IMAGE in qwen35.input_modalities
