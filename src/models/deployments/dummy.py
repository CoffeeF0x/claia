"""
Dummy deployment plugin.

Provides deployment capabilities for the dummy model.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Internal dependencies
from ..hooks.deployment import DeploymentInfo, DeploymentStatus
from ..base import BaseModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                         DEPLOYMENT PLUGIN                            #
########################################################################
class DummyDeploymentPlugin:
    """Deployment plugin for dummy models."""

    def get_deployment_info(self) -> DeploymentInfo:
        """Get deployment information for dummy models."""
        return DeploymentInfo(
            name="dummy",
            title="Dummy Deployment",
            description="Local deployment for dummy model testing",
            supported_architectures=["DummyModel"],
            supported_models=["dummy-model"],
            deployment_type="local",
            requirements={},
            configuration={
                "words_per_second": {
                    "type": "integer",
                    "default": 20,
                    "description": "Streaming speed in words per second"
                }
            }
        )

    def get_deployment_status(self, model_name: str, config: Dict[str, Any]) -> DeploymentStatus:
        """Get deployment status for dummy model."""
        # Dummy deployment is always available locally
        return DeploymentStatus(
            available=True,
            ready=True,
            message="Dummy model ready for testing",
            details={
                "deployment": "dummy",
                "location": "local",
                "type": "test"
            }
        )

    def deploy_model(self, model_name: str, config: Dict[str, Any]) -> BaseModel:
        """Deploy the dummy model."""
        # For dummy deployment, we just return the model instance
        from ..architectures.dummy_architecture import DummyModel
        return DummyModel(config)

    def undeploy_model(self, model_name: str) -> bool:
        """Undeploy the dummy model."""
        # Dummy models don't need explicit cleanup
        return True

    def is_supported(self, model_name: str, architecture: str) -> bool:
        """Check if this deployment supports the given model."""
        return model_name == "dummy-model" and architecture == "DummyModel"
