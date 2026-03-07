"""
Dummy deployment plugin.

Provides deployment capabilities for the dummy model.
"""

import logging
import pluggy
from typing import Dict, Any, Type, Iterator

# Internal dependencies
from claia.lib.data import Conversation
from ..hooks.deployment import DeploymentInfo



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("claia_deployments")



########################################################################
#                         DEPLOYMENT PLUGIN                            #
########################################################################
class DummyDeploymentPlugin:
    """Deployment plugin for dummy models."""

    @hookimpl
    def get_deployment_info(self) -> DeploymentInfo:
        """Get deployment information for dummy models."""
        return DeploymentInfo(
            name="dummy",
            title="Dummy Deployment",
            description="Dummy local deployment for testing"
        )

    @hookimpl
    def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Iterator[str]:
        """Deploy (if needed) and run inference for dummy model. Yields tokens."""
        cache_key = f"{model_name}:dummy"

        if cache_key in cache:
            model_instance = cache[cache_key]
            logger.debug(f"Using cached dummy model instance for {cache_key}")
        else:
            logger.debug(f"Deploying dummy model: {model_name}")
            model_instance = model_class(model_name=model_name)
            cache[cache_key] = model_instance
            logger.debug(f"Successfully deployed and cached dummy model: {model_name}")

        logger.debug(f"Running dummy model inference: {model_name}")
        yield from model_instance.generate(conversation, **kwargs)
