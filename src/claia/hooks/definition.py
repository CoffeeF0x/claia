"""
Pluggy hookspecs for definition-provider plugins.

These specs mirror ``BaseDefinitionProvider`` in
``claia_core.definitions.base``.
"""

import pluggy
from typing import Dict

from claia_core.definitions.model_definition import ModelDefinition


hookspec = pluggy.HookspecMarker("claia_definitions")


class DefinitionHooks:
  """Hook specifications for model-definition plugins."""

  @hookspec
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Return the model definitions contributed by this provider."""


__all__ = ["DefinitionHooks", "ModelDefinition"]
