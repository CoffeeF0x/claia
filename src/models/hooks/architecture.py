"""
Hook specifications for architecture plugins.

Architecture plugins implement specific AI model architectures
(e.g., OpenAI models, Anthropic models, Transformers, etc.)
"""

import pluggy
from typing import Optional, Type


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_architectures")


class ArchitectureHooks:
  """Hook specifications for architecture plugins."""

  @hookspec
  def get_model_class(self, model_name: str) -> Optional[Type]:
    """
    Get the model class for a specific model.

    Args:
        model_name: Canonical model name

    Returns:
        Model class if supported, None otherwise
    """
