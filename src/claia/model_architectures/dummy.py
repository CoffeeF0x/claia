"""
Dummy model architecture plugin.

Provides the architecture implementation for the dummy streaming model.
"""

import logging
import pluggy
from typing import Type

# Internal dependencies
from ..lib.model.dummy import DummyModel
from ..hooks.architecture import ArchitectureInfo


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Create hookimpl decorator for this plugin namespace
hookimpl = pluggy.HookimplMarker("claia_architectures")


########################################################################
#                               CLASSES                                #
########################################################################
class DummyArchitecturePlugin:
  """Dummy architecture plugin for testing purposes."""

  @hookimpl
  def get_architecture_info(self) -> ArchitectureInfo:
    """Provide metadata about this architecture plugin."""
    return ArchitectureInfo(
      name="dummy",
      title="Dummy Architecture",
      description="Dummy local model architecture for testing"
    )

  @hookimpl
  def get_model_class(self) -> Type:
    """Return the DummyModel class for this architecture."""
    logger.debug("Providing DummyModel class for dummy architecture")
    return DummyModel
