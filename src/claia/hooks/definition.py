"""
Hook specifications for model definition plugins.

Definition plugins provide metadata about models (names, aliases, providers, etc.)
without implementing the actual model functionality.
"""

import pluggy
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

# Internal dependencies
from claia.lib.results import Result


@dataclass
class ModelDefinition:
  """Definition of a model provided by a definition plugin."""
  title: Optional[str] = None                  # Human-readable title
  aliases: Optional[List[str]] = None          # Alternative names/aliases
  company: Optional[str] = None                # Company/organization that created the model
  deployments: Optional[List[str]] = None      # Deployment methods that support this model
  architectures: Optional[List[str]] = None    # Model implementation classes that can handle this
  description: Optional[str] = None            # Description of the model
  parameters: Optional[str] = None             # Parameter count (e.g., "7B", "70B", "175B")
  context_length: Optional[int] = None         # Maximum context length
  capabilities: Optional[List[str]] = None     # Model capabilities (e.g., ["chat", "code", "vision"])
  license: Optional[str] = None                # Model license
  url: Optional[str] = None                    # Homepage or documentation URL
  identifiers: Optional[Dict[str, str]] = None # Mapping: architecture_name -> model identifier for that architecture


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_definitions")


class DefinitionHooks:
  """Hook specifications for model definition plugins."""

  @hookspec
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """
    Get model definitions provided by this plugin.

    Returns:
        Dict mapping model names to ModelDefinition objects
    """
