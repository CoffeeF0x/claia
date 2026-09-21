"""Z.ai / GLM model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk, ToolChunk
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
        outputs=[TextChunk, ToolChunk],
      ),

      "glm-5.3-flash": ModelDefinition(
        title="GLM 5.3 Flash",
        aliases=["glm-flash"],
        company="Z.ai",
        architectures=["openrouter"],
        description="Native multimodal GLM 5.3 for efficient coding and long-horizon agent tasks",
        context_length=1310720,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        license="Open Source",
        url="https://openrouter.ai/models/z-ai/glm-5.3-flash",
        identifiers={"openrouter": "z-ai/glm-5.3-flash"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk, ToolChunk],
      ),

      "glm-5.3-flashx": ModelDefinition(
        title="GLM 5.3 FlashX",
        aliases=["glm-flashx"],
        company="Z.ai",
        architectures=["openrouter"],
        description="High-speed GLM 5.3 Flash variant for coding, vision, and long-horizon agents",
        context_length=1048576,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        license="Open Source",
        url="https://openrouter.ai/models/z-ai/glm-5.3-flashx",
        identifiers={"openrouter": "z-ai/glm-5.3-flashx"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk, ToolChunk],
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
        outputs=[TextChunk, ToolChunk],
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
        outputs=[TextChunk, ToolChunk],
      ),
    }
