"""Moonshot AI / Kimi model definitions (OpenRouter)."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ._openrouter import VISION, definition
from ..decorators import definitions


@definitions
@definitions.name("moonshot")
@definitions.title("Moonshot AI Definitions")
@definitions.description("Moonshot AI / Kimi models available through OpenRouter.")
class MoonshotDefinitions(BaseDefinitionProvider):
  """Moonshot AI model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    return {
      "kimi-k3": definition(
        title="Kimi K3",
        provider_id="moonshotai/kimi-k3",
        company="Moonshot AI",
        aliases=["kimi", "kimi-k3"],
        description="Open-weight multimodal reasoning model for long-horizon coding and knowledge work.",
        context_length=1048576,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        inputs=VISION,
        license="Open Weights",
      ),
      "kimi-k2.7-code": definition(
        title="Kimi K2.7 Code",
        provider_id="moonshotai/kimi-k2.7-code",
        company="Moonshot AI",
        aliases=["kimi-k2.7", "kimi-code"],
        description="Coding-focused multimodal MoE for long-horizon programming and agentic decomposition.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        inputs=VISION,
        license="Open Weights",
      ),
      "kimi-k2.6": definition(
        title="Kimi K2.6",
        provider_id="moonshotai/kimi-k2.6",
        company="Moonshot AI",
        aliases=["kimi-k2", "kimi-k2-6"],
        description="Multimodal model for long-horizon coding and multi-agent orchestration.",
        context_length=256000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        inputs=VISION,
        license="Open Weights",
      ),
      "kimi-k2.5": definition(
        title="Kimi K2.5",
        provider_id="moonshotai/kimi-k2.5",
        company="Moonshot AI",
        aliases=["kimi-k2-5"],
        description="Multimodal Kimi K2 continuation with strong visual coding and agentic performance.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        inputs=VISION,
        license="Open Weights",
      ),
      "kimi-k2-thinking": definition(
        title="Kimi K2 Thinking",
        provider_id="moonshotai/kimi-k2-thinking",
        company="Moonshot AI",
        aliases=["kimi-thinking"],
        description="Open reasoning MoE model optimized for step-by-step reasoning, tool use, and long workflows.",
        context_length=256000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
    }
