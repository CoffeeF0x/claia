"""OpenRouter-only model definitions plugin."""

import logging
from typing import Dict, List, Optional

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition, artifacts_from_modalities
from ..decorators import definitions
from ..modality import Modality
from ..data.models.conversation.message_sequence import MessageSequence


logger = logging.getLogger(__name__)


def _definition(
  title: str,
  provider_id: str,
  company: str,
  description: str,
  context_length: int,
  capabilities: List[str],
  aliases: Optional[List[str]] = None,
  input_modalities: Optional[List[Modality]] = None,
  license: str = "Commercial",
  url: Optional[str] = None,
) -> ModelDefinition:
  """Build a definition for a model primarily exposed through OpenRouter."""
  modalities = input_modalities or [Modality.TEXT]
  return ModelDefinition(
    title=title,
    aliases=aliases,
    company=company,
    deployments=["api"],
    architectures=["openrouter"],
    description=description,
    context_length=context_length,
    capabilities=capabilities,
    license=license,
    url=url or f"https://openrouter.ai/models/{provider_id}",
    identifiers={"openrouter": provider_id},
    input_modalities=modalities,
    output_modalities=[Modality.TEXT],
    supported_inputs=[*artifacts_from_modalities(modalities), MessageSequence],
  )


@definitions
class OpenRouterDefinitionsPlugin(BaseDefinitionProvider):
  """OpenRouter model definitions plugin."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get large non-native provider models available through OpenRouter."""
    vision = [Modality.TEXT, Modality.IMAGE]
    return {
      # ----------------------------------------------------------------
      # Moonshot AI / Kimi
      # ----------------------------------------------------------------
      "kimi-k2.6": _definition(
        title="Kimi K2.6",
        provider_id="moonshotai/kimi-k2.6",
        company="Moonshot AI",
        aliases=["kimi", "kimi-k2", "kimi-k2-6"],
        description="Next-generation multimodal model for long-horizon coding and multi-agent orchestration.",
        context_length=256000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        input_modalities=vision,
        license="Open Weights",
      ),
      "kimi-k2.5": _definition(
        title="Kimi K2.5",
        provider_id="moonshotai/kimi-k2.5",
        company="Moonshot AI",
        aliases=["kimi-k2-5"],
        description="Multimodal Kimi K2 continuation with strong visual coding and agentic performance.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        input_modalities=vision,
        license="Open Weights",
      ),
      "kimi-k2-thinking": _definition(
        title="Kimi K2 Thinking",
        provider_id="moonshotai/kimi-k2-thinking",
        company="Moonshot AI",
        aliases=["kimi-thinking"],
        description="Open reasoning MoE model optimized for step-by-step reasoning, tool use, and long workflows.",
        context_length=256000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),

      # ----------------------------------------------------------------
      # DeepSeek
      # ----------------------------------------------------------------
      "deepseek-v4-pro": _definition(
        title="DeepSeek V4 Pro",
        provider_id="deepseek/deepseek-v4-pro",
        company="DeepSeek",
        aliases=["deepseek-pro", "deepseek-v4"],
        description="Large DeepSeek V4 MoE reasoning and coding model with a 1M-token context window.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Source",
      ),
      "deepseek-v4-flash": _definition(
        title="DeepSeek V4 Flash",
        provider_id="deepseek/deepseek-v4-flash",
        company="DeepSeek",
        aliases=["deepseek-flash"],
        description="Efficiency-optimized DeepSeek V4 MoE model for fast, high-throughput reasoning and coding.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Source",
      ),
      "deepseek-r1-0528": _definition(
        title="DeepSeek R1 0528",
        provider_id="deepseek/deepseek-r1-0528",
        company="DeepSeek",
        aliases=["deepseek-r1", "r1"],
        description="Open reasoning model update with strong math, coding, and tool-use performance.",
        context_length=163840,
        capabilities=["chat", "code", "reasoning", "tool_use", "structured_outputs"],
        license="Open Source",
      ),

      # ----------------------------------------------------------------
      # MiniMax
      # ----------------------------------------------------------------
      "minimax-m2.7": _definition(
        title="MiniMax M2.7",
        provider_id="minimax/minimax-m2.7",
        company="MiniMax",
        aliases=["minimax"],
        description="Next-generation productivity and autonomous-agent model for multi-agent collaboration.",
        context_length=204800,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "minimax-m2.5": _definition(
        title="MiniMax M2.5",
        provider_id="minimax/minimax-m2.5",
        company="MiniMax",
        aliases=["minimax-m2-5"],
        description="Productivity-focused model for real-world office and agent workflows.",
        context_length=196608,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "minimax-m2": _definition(
        title="MiniMax M2",
        provider_id="minimax/minimax-m2",
        company="MiniMax",
        description="MoE model optimized for coding and agentic workflows.",
        context_length=196608,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "minimax-m1": _definition(
        title="MiniMax M1",
        provider_id="minimax/minimax-m1",
        company="MiniMax",
        description="Large-scale MoE reasoning model with a 1M-token context window.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Weights",
      ),

      # ----------------------------------------------------------------
      # Z.ai / GLM
      # ----------------------------------------------------------------
      "glm-5.1": _definition(
        title="GLM 5.1",
        provider_id="z-ai/glm-5.1",
        company="Z.ai",
        aliases=["glm", "z-ai-glm"],
        description="Long-horizon agent model for autonomous planning, execution, and iterative improvement.",
        context_length=202752,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),
      "glm-5": _definition(
        title="GLM 5",
        provider_id="z-ai/glm-5",
        company="Z.ai",
        aliases=["glm-5"],
        description="Flagship open-source model for complex systems design and long-horizon agent workflows.",
        context_length=202752,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),
      "glm-4.5": _definition(
        title="GLM 4.5",
        provider_id="z-ai/glm-4.5",
        company="Z.ai",
        aliases=["glm-4-5"],
        description="MoE foundation model for agent-based applications with thinking and non-thinking modes.",
        context_length=131072,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),

      # ----------------------------------------------------------------
      # Qwen
      # ----------------------------------------------------------------
      "qwen3.6-plus": _definition(
        title="Qwen3.6 Plus",
        provider_id="qwen/qwen3.6-plus",
        company="Alibaba Cloud",
        aliases=["qwen3.6", "qwen-plus"],
        description="Hybrid architecture model with 1M-token context for agentic coding, front-end work, and reasoning.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic", "multilingual"],
        license="Commercial",
      ),
      "qwen3.6-plus-preview": _definition(
        title="Qwen3.6 Plus Preview",
        provider_id="qwen/qwen3.6-plus-preview",
        company="Alibaba Cloud",
        aliases=["qwen3.6-preview"],
        description="Preview release of Qwen3.6 Plus with 1M-token context for coding and reasoning workflows.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic", "multilingual"],
        license="Commercial",
      ),
      "qwen3.5-397b-a17b": _definition(
        title="Qwen3.5 397B A17B",
        provider_id="qwen/qwen3.5-397b-a17b",
        company="Alibaba Cloud",
        aliases=["qwen3.5", "qwen3.5-large"],
        description="Largest Qwen3.5 native vision-language model for reasoning and long-context work.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        input_modalities=vision,
        license="Commercial",
      ),
      "qwen3.5-122b-a10b": _definition(
        title="Qwen3.5 122B A10B",
        provider_id="qwen/qwen3.5-122b-a10b",
        company="Alibaba Cloud",
        aliases=["qwen3.5-122b"],
        description="Large Qwen3.5 hybrid vision-language model for reasoning and coding.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        input_modalities=vision,
        license="Commercial",
      ),
      "qwen3.5-35b-a3b": _definition(
        title="Qwen3.5 35B A3B",
        provider_id="qwen/qwen3.5-35b-a3b",
        company="Alibaba Cloud",
        aliases=["qwen3.5-35b"],
        description="Sparse Qwen3.5 vision-language MoE for efficient reasoning and coding.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        input_modalities=vision,
        license="Commercial",
      ),
      "qwen3.5-27b": _definition(
        title="Qwen3.5 27B",
        provider_id="qwen/qwen3.5-27b",
        company="Alibaba Cloud",
        description="Dense Qwen3.5 vision-language model for general reasoning and coding tasks.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        input_modalities=vision,
        license="Commercial",
      ),
      "qwen3.5-flash": _definition(
        title="Qwen3.5 Flash",
        provider_id="qwen/qwen3.5-flash-02-23",
        company="Alibaba Cloud",
        aliases=["qwen3.5-fast"],
        description="Fast Qwen3.5 vision-language model with a 1M-token context window.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        input_modalities=vision,
        license="Commercial",
      ),
      "qwen3-max": _definition(
        title="Qwen3 Max",
        provider_id="qwen/qwen3-max",
        company="Alibaba Cloud",
        aliases=["qwen-max", "qwen"],
        description="Large Qwen model for reasoning, multilingual work, coding, and tool calling.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "tool_use", "multilingual"],
        license="Commercial",
      ),
      "qwen3-coder": _definition(
        title="Qwen3 Coder 480B A35B",
        provider_id="qwen/qwen3-coder",
        company="Alibaba Cloud",
        aliases=["qwen-coder"],
        description="Open-weight MoE coding model for agentic coding, tool use, and repository-scale context.",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "qwen3-coder-next": _definition(
        title="Qwen3 Coder Next",
        provider_id="qwen/qwen3-coder-next",
        company="Alibaba Cloud",
        aliases=["qwen-coder-next"],
        description="Efficient open-weight coding MoE for coding agents and local development workflows.",
        context_length=262144,
        capabilities=["chat", "code", "tool_use", "agentic"],
        license="Open Weights",
      ),

      # ----------------------------------------------------------------
      # Meta Llama
      # ----------------------------------------------------------------
      "llama-4-maverick": _definition(
        title="Llama 4 Maverick",
        provider_id="meta-llama/llama-4-maverick",
        company="Meta",
        aliases=["llama-maverick", "llama-4"],
        description="Large multimodal MoE model with broad multilingual text and code capabilities.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "multilingual"],
        input_modalities=vision,
        license="Llama 4 Community License",
      ),
      "llama-4-scout": _definition(
        title="Llama 4 Scout",
        provider_id="meta-llama/llama-4-scout",
        company="Meta",
        aliases=["llama-scout"],
        description="Multimodal MoE model with an extremely long context window.",
        context_length=10000000,
        capabilities=["chat", "code", "vision", "multilingual"],
        input_modalities=vision,
        license="Llama 4 Community License",
      ),
    }
