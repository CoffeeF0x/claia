"""Alibaba / Qwen model definitions (OpenRouter)."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ._openrouter import VISION, definition
from ..decorators import definitions


@definitions
@definitions.name("qwen")
@definitions.title("Qwen Definitions")
@definitions.description("Alibaba Cloud Qwen models available through OpenRouter.")
class QwenDefinitions(BaseDefinitionProvider):
  """Qwen model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    return {
      "qwen3.6-plus": definition(
        title="Qwen3.6 Plus",
        provider_id="qwen/qwen3.6-plus",
        company="Alibaba Cloud",
        aliases=["qwen3.6", "qwen-plus", "qwen"],
        description="Hybrid architecture model with 1M-token context for agentic coding, front-end work, and reasoning.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic", "multilingual"],
        inputs=VISION,
        license="Commercial",
      ),
      "qwen3.6-plus-preview": definition(
        title="Qwen3.6 Plus Preview",
        provider_id="qwen/qwen3.6-plus-preview",
        company="Alibaba Cloud",
        aliases=["qwen3.6-preview"],
        description="Preview release of Qwen3.6 Plus with 1M-token context for coding and reasoning workflows.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic", "multilingual"],
        inputs=VISION,
        license="Commercial",
      ),
      "qwen3.5-397b-a17b": definition(
        title="Qwen3.5 397B A17B",
        provider_id="qwen/qwen3.5-397b-a17b",
        company="Alibaba Cloud",
        aliases=["qwen3.5", "qwen3.5-large"],
        description="Largest Qwen3.5 native vision-language model for reasoning and long-context work.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        inputs=VISION,
        license="Commercial",
      ),
      "qwen3.5-122b-a10b": definition(
        title="Qwen3.5 122B A10B",
        provider_id="qwen/qwen3.5-122b-a10b",
        company="Alibaba Cloud",
        aliases=["qwen3.5-122b"],
        description="Large Qwen3.5 hybrid vision-language model for reasoning and coding.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        inputs=VISION,
        license="Commercial",
      ),
      "qwen3.5-35b-a3b": definition(
        title="Qwen3.5 35B A3B",
        provider_id="qwen/qwen3.5-35b-a3b",
        company="Alibaba Cloud",
        aliases=["qwen3.5-35b"],
        description="Sparse Qwen3.5 vision-language MoE for efficient reasoning and coding.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        inputs=VISION,
        license="Commercial",
      ),
      "qwen3.5-27b": definition(
        title="Qwen3.5 27B",
        provider_id="qwen/qwen3.5-27b",
        company="Alibaba Cloud",
        description="Dense Qwen3.5 vision-language model for general reasoning and coding tasks.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        inputs=VISION,
        license="Commercial",
      ),
      "qwen3.5-flash": definition(
        title="Qwen3.5 Flash",
        provider_id="qwen/qwen3.5-flash-02-23",
        company="Alibaba Cloud",
        aliases=["qwen3.5-fast"],
        description="Fast Qwen3.5 vision-language model with a 1M-token context window.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        inputs=VISION,
        license="Commercial",
      ),
      "qwen3-max": definition(
        title="Qwen3 Max",
        provider_id="qwen/qwen3-max",
        company="Alibaba Cloud",
        aliases=["qwen-max"],
        description="Large Qwen model for reasoning, multilingual work, coding, and tool calling.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "tool_use", "multilingual"],
        license="Commercial",
      ),
      "qwen3-coder": definition(
        title="Qwen3 Coder 480B A35B",
        provider_id="qwen/qwen3-coder",
        company="Alibaba Cloud",
        aliases=["qwen-coder"],
        description="Open-weight MoE coding model for agentic coding, tool use, and repository-scale context.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "qwen3-coder-next": definition(
        title="Qwen3 Coder Next",
        provider_id="qwen/qwen3-coder-next",
        company="Alibaba Cloud",
        aliases=["qwen-coder-next"],
        description="Efficient open-weight coding MoE for coding agents and local development workflows.",
        context_length=262144,
        capabilities=["chat", "code", "tool_use", "agentic"],
        license="Open Weights",
      ),
    }
