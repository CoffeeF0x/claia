"""Alibaba / Qwen model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence


@definitions
@definitions.name("qwen")
@definitions.title("Qwen Definitions")
@definitions.description("Alibaba Cloud Qwen models available through OpenRouter.")
class QwenDefinitions(BaseDefinitionProvider):
  """Qwen model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Qwen model definitions."""
    return {
      "qwen3.6-plus": ModelDefinition(
        title="Qwen3.6 Plus",
        aliases=["qwen3.6", "qwen-plus", "qwen"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Hybrid architecture model with 1M-token context for agentic coding, front-end work, and reasoning",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3.6-plus",
        identifiers={"openrouter": "qwen/qwen3.6-plus"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3.6-plus-preview": ModelDefinition(
        title="Qwen3.6 Plus Preview",
        aliases=["qwen3.6-preview"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Preview release of Qwen3.6 Plus with 1M-token context for coding and reasoning workflows",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3.6-plus-preview",
        identifiers={"openrouter": "qwen/qwen3.6-plus-preview"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3.5-397b-a17b": ModelDefinition(
        title="Qwen3.5 397B A17B",
        aliases=["qwen3.5", "qwen3.5-large"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Largest Qwen3.5 native vision-language model for reasoning and long-context work",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3.5-397b-a17b",
        identifiers={"openrouter": "qwen/qwen3.5-397b-a17b"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3.5-122b-a10b": ModelDefinition(
        title="Qwen3.5 122B A10B",
        aliases=["qwen3.5-122b"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Large Qwen3.5 hybrid vision-language model for reasoning and coding",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3.5-122b-a10b",
        identifiers={"openrouter": "qwen/qwen3.5-122b-a10b"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3.5-35b-a3b": ModelDefinition(
        title="Qwen3.5 35B A3B",
        aliases=["qwen3.5-35b"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Sparse Qwen3.5 vision-language MoE for efficient reasoning and coding",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3.5-35b-a3b",
        identifiers={"openrouter": "qwen/qwen3.5-35b-a3b"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3.5-27b": ModelDefinition(
        title="Qwen3.5 27B",
        aliases=None,
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Dense Qwen3.5 vision-language model for general reasoning and coding tasks",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3.5-27b",
        identifiers={"openrouter": "qwen/qwen3.5-27b"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3.5-flash": ModelDefinition(
        title="Qwen3.5 Flash",
        aliases=["qwen3.5-fast"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Fast Qwen3.5 vision-language model with a 1M-token context window",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3.5-flash-02-23",
        identifiers={"openrouter": "qwen/qwen3.5-flash-02-23"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3-max": ModelDefinition(
        title="Qwen3 Max",
        aliases=["qwen-max"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Large Qwen model for reasoning, multilingual work, coding, and tool calling",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "tool_use", "multilingual"],
        license="Commercial",
        url="https://openrouter.ai/models/qwen/qwen3-max",
        identifiers={"openrouter": "qwen/qwen3-max"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3-coder": ModelDefinition(
        title="Qwen3 Coder 480B A35B",
        aliases=["qwen-coder"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Open-weight MoE coding model for agentic coding, tool use, and repository-scale context",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/qwen/qwen3-coder",
        identifiers={"openrouter": "qwen/qwen3-coder"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "qwen3-coder-next": ModelDefinition(
        title="Qwen3 Coder Next",
        aliases=["qwen-coder-next"],
        company="Alibaba Cloud",
        deployments=["api"],
        architectures=["openrouter"],
        description="Efficient open-weight coding MoE for coding agents and local development workflows",
        context_length=262144,
        capabilities=["chat", "code", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/qwen/qwen3-coder-next",
        identifiers={"openrouter": "qwen/qwen3-coder-next"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),
    }
