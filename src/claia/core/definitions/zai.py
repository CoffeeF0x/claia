"""Z.ai / GLM model definitions (OpenRouter)."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ._openrouter import definition
from ..decorators import definitions


@definitions
@definitions.name("zai")
@definitions.title("Z.ai Definitions")
@definitions.description("Z.ai / GLM models available through OpenRouter.")
class ZaiDefinitions(BaseDefinitionProvider):
  """Z.ai model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    return {
      "glm-5.3": definition(
        title="GLM 5.3",
        identifiers={"openrouter": "z-ai/glm-5.3"},
        company="Z.ai",
        aliases=["glm", "z-ai-glm"],
        description="Large-scale reasoning model for complex software engineering and long-horizon agent tasks.",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),
      "glm-5.2": definition(
        title="GLM 5.2",
        identifiers={"openrouter": "z-ai/glm-5.2"},
        company="Z.ai",
        aliases=["glm-5-2"],
        description="Long-horizon agent model for project-level software engineering and multi-step automation.",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),
      "glm-5.1": definition(
        title="GLM 5.1",
        identifiers={"openrouter": "z-ai/glm-5.1"},
        company="Z.ai",
        aliases=["glm-5-1"],
        description="Long-horizon agent model for autonomous planning, execution, and iterative improvement.",
        context_length=202752,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),
      "glm-5": definition(
        title="GLM 5",
        identifiers={"openrouter": "z-ai/glm-5"},
        company="Z.ai",
        description="Flagship open-source model for complex systems design and long-horizon agent workflows.",
        context_length=202752,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),
      "glm-4.5": definition(
        title="GLM 4.5",
        identifiers={"openrouter": "z-ai/glm-4.5"},
        company="Z.ai",
        aliases=["glm-4-5"],
        description="MoE foundation model for agent-based applications with thinking and non-thinking modes.",
        context_length=131072,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Source",
      ),
    }
