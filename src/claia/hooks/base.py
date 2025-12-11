"""
Base class for extension info dataclasses.

All plugin types share a common interface for configuration and discovery.
This base class provides the consistent fields that the Manager and Registry
use for filtering kwargs and collecting extension metadata.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ExtensionInfo:
  """
  Base information class for all CLAIA extension plugins.
  
  This provides a consistent interface across all plugin types:
  - Architectures, Deployments, Solvers, Patterns, Protocols, Tool Modules
  
  The required_args field allows plugins to declare which settings they need,
  enabling the Manager to filter kwargs and the Settings class to dynamically
  add extension-specific configuration options.
  
  Attributes:
    name: Unique identifier for the extension (used in lookups)
    title: Human-readable display name
    description: Description of what the extension does
    required_args: List of setting names this extension needs from Settings
  """
  name: str
  title: str
  description: str
  required_args: Optional[List[str]] = None

