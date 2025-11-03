"""
Hook specifications for deployment method plugins.

Deployment method plugins handle specific ways to deploy/run models
(e.g., local execution, remote API calls, cloud VMs, etc.)
"""

import pluggy
from typing import Optional, Dict, List, Any, Type
from dataclasses import dataclass

# Internal dependencies
from claia.lib.results import Result
from claia.lib.data import Conversation


@dataclass
class DeploymentInfo:
  """Information about a deployment method provided by a deployment plugin."""
  name: str
  title: str
  description: str
  required_args: Optional[List[str]] = None # list of custom args required by the deployment method


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_deployments")


class DeploymentHooks:
  """Hook specifications for deployment method plugins."""

  @hookspec
  def get_deployment_info(self) -> DeploymentInfo:
    """
    Get information about this deployment method.

    Returns:
        DeploymentInfo object describing this deployment method
    """

  @hookspec
  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Result:
    """
    Deploy (if needed) and run inference on a model.

    This method handles both model deployment/caching and running inference.
    The deployment plugin manages its own model instances and caching strategies.

    Args:
        model_name: Canonical model name
        model_class: Model class to instantiate
        conversation: Conversation to process
        cache: Cache dictionary for model instances (deployment plugin manages this)
        **kwargs: Additional deployment and runtime parameters

    Returns:
        Result containing the model response or error
    """
