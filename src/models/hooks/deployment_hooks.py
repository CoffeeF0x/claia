"""
Hook specifications for deployment method plugins.

Deployment method plugins handle specific ways to deploy/run models
(e.g., local execution, remote API calls, cloud VMs, etc.)
"""

import pluggy
from typing import Optional, Dict, List, Any, Type
from dataclasses import dataclass

# Internal dependencies
from common.results import Result
from common.files.conversation import Conversation


@dataclass
class DeploymentInfo:
  """Information about a deployment method provided by a deployment plugin."""
  name: str
  title: str
  description: str
  supported_model_types: List[str]  # e.g., ['api', 'transformers', 'custom']
  requires_api_key: bool = False
  settings: Optional[Dict[str, Any]] = None


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
  def can_deploy_model(self, model_name: str, model_type: str) -> bool:
    """
    Check if this deployment method can handle the specified model.

    Args:
        model_name: Canonical model name
        model_type: Model type (e.g., 'api', 'transformers')

    Returns:
        True if this deployment method can handle the model
    """

  @hookspec
  def deploy_model(self, model_name: str, model_class: Type, **kwargs) -> Result:
    """
    Deploy/initialize a model using this deployment method.

    Args:
        model_name: Canonical model name
        model_class: Model class to instantiate
        **kwargs: Additional deployment parameters (api_keys, device, etc.)

    Returns:
        Result containing the deployed model instance or error
    """

  @hookspec
  def run_model(self, model_instance: Any, conversation: Conversation, **kwargs) -> Result:
    """
    Run inference on a deployed model.

    Args:
        model_instance: The deployed model instance
        conversation: Conversation to process
        **kwargs: Additional runtime parameters

    Returns:
        Result containing the model response or error
    """
