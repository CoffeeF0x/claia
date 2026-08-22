"""Z.ai / GLM model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence


@definitions
@definitions.name("zai")
@definitions.title("Z.ai Definitions")
@definitions.description("Z.ai / GLM models available through OpenRouter.")
class ZaiDefinitions(BaseDefinitionProvider):
  """Z.ai model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Z.ai model definitions."""
    return {
      "glm-5.3": ModelDefinition(
        title="GLM 5.3",
        aliases=["glm", "z-ai-glm"],
        company="Z.ai",
        architectures=["openrouter"],
        description="Large-scale reasoning model for complex software engineering and long-horizon agent tasks",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
        url="https://openrouter.ai/models/z-ai/glm-5.3",
        identifiers={"openrouter": "z-ai/glm-5.3"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "glm-5.2": ModelDefinition(
        title="GLM 5.2",
        aliases=["glm-5-2"],
        company="Z.ai",
        architectures=["openrouter"],
        description="Long-horizon agent model for project-level software engineering and multi-step automation",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
        url="https://openrouter.ai/models/z-ai/glm-5.2",
        identifiers={"openrouter": "z-ai/glm-5.2"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "glm-5.1": ModelDefinition(
        title="GLM 5.1",
        aliases=["glm-5-1"],
        company="Z.ai",
        architectures=["openrouter"],
        description="Long-horizon agent model for autonomous planning, execution, and iterative improvement",
        context_length=202752,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
        url="https://openrouter.ai/models/z-ai/glm-5.1",
        identifiers={"openrouter": "z-ai/glm-5.1"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "glm-5": ModelDefinition(
        title="GLM 5",
        aliases=None,
        company="Z.ai",
        architectures=["openrouter"],
        description="Flagship open-source model for complex systems design and long-horizon agent workflows",
        context_length=202752,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
        url="https://openrouter.ai/models/z-ai/glm-5",
        identifiers={"openrouter": "z-ai/glm-5"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "glm-4.5": ModelDefinition(
        title="GLM 4.5",
        aliases=["glm-4-5"],
        company="Z.ai",
        architectures=["openrouter"],
        description="MoE foundation model for agent-based applications with thinking and non-thinking modes",
        context_length=131072,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
        url="https://openrouter.ai/models/z-ai/glm-4.5",
        identifiers={"openrouter": "z-ai/glm-4.5"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),
    }
