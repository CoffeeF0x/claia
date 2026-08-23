"""
Dummy deployment.

Serves the dummy architecture; also the minimal reference for the
deployment seam.
"""

from typing import Any

from .base import BaseDeployment
from ..data.request import AgentRequest
from ..decorators import deployment


@deployment
@deployment.name("dummy")
@deployment.title("Dummy Deployment")
@deployment.description("Dummy in-process deployment for testing")
class DummyDeployment(BaseDeployment):
  """Deployment for the dummy architecture."""

  def deploy(self, request: AgentRequest) -> Any:
    # The dummy architecture takes no init-time configuration.
    return request.architecture_class(model_name=request.provider_model)
