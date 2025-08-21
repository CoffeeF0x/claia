"""
Hook specifications for architecture plugins.

Architecture plugins implement specific AI model architectures
(e.g., OpenAI models, Anthropic models, Transformers, etc.)
"""

import pluggy
from typing import Type, Optional, List
from dataclasses import dataclass


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_architectures")


@dataclass
class ArchitectureInfo:
  """Information about an architecture plugin."""
  name: str
  title: str
  description: str
  required_args: Optional[List[str]] = None  # list of custom args required by the architecture


class ArchitectureHooks:
  """Hook specifications for architecture plugins."""

  @hookspec
  def get_architecture_info(self) -> ArchitectureInfo:
    """
    Get information about this architecture plugin.

    Returns:
        ArchitectureInfo describing this plugin
    """

  @hookspec
  def get_model_class(self) -> Type:
    """
    Get the model class implemented by this architecture plugin.

    Returns:
        Model class type
    """
