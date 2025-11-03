"""
Dummy deployment plugin.

Provides deployment capabilities for the dummy model.
"""

import logging
import pluggy
from typing import Dict, Any, Type

# Internal dependencies
from claia.lib.results import Result
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
    def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Result:
        """Unified run(): deploy (if needed) and run inference for dummy model."""
        try:
            cache_key = f"{model_name}:dummy"

            # Use cached instance if available
            if cache_key in cache:
                model_instance = cache[cache_key]
                logger.debug(f"Using cached dummy model instance for {cache_key}")
            else:
                logger.debug(f"Deploying dummy model: {model_name}")
                # DummyModel takes only model_name
                model_instance = model_class(model_name=model_name)
                cache[cache_key] = model_instance
                logger.debug(f"Successfully deployed and cached dummy model: {model_name}")

            # Run inference
            logger.debug(f"Running dummy model inference: {model_name}")
            try:
                output = model_instance.generate(conversation, **kwargs)
            except Exception as e:
                logger.error(f"Error during dummy model generate(): {e}")
                return Result.fail(f"Dummy model generate() failed: {e}")

            return output if isinstance(output, Result) else Result.ok(output)

        except Exception as e:
            logger.error(f"Error running dummy model {model_name}: {str(e)}")
            return Result.fail(f"Failed to run dummy model: {str(e)}")
