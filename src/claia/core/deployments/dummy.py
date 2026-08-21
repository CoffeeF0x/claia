"""
Dummy deployment.

Provides deployment capabilities for the dummy model.
"""

from .base import BaseDeployment
from ..decorators import deployment


@deployment
@deployment.name("dummy")
@deployment.title("Dummy Deployment")
@deployment.description("Dummy local deployment for testing")
class DummyDeployment(BaseDeployment):
  """Deployment for dummy models."""

  def create_model(self, model_name, model_class, init_kwargs):
    # DummyModel takes no init-time configuration.
    return model_class(model_name=model_name)
