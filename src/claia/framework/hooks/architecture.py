"""
Pluggy hookspecs for architecture plugins.

These specs mirror the ``BaseArchitecture`` ABC defined in
``claia.core.architectures.base``: the ABC defines what a plugin must
implement; the hookspec defines how the framework discovers and dispatches
to those plugins.
"""

import pluggy
from typing import Type

from claia.core.plugins.base import ArchitectureInfo


hookspec = pluggy.HookspecMarker("claia_architectures")


class ArchitectureHooks:
  """Hook specifications for architecture plugins."""

  @hookspec
  def get_architecture_info(self) -> ArchitectureInfo:
    """Return metadata describing this architecture."""

  @hookspec
  def get_model_class(self) -> Type:
    """Return the concrete model class implemented by this architecture."""


__all__ = ["ArchitectureHooks", "ArchitectureInfo"]
