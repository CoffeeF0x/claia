"""
Dummy deployment plugin.

Provides deployment capabilities for the dummy model.
"""

from .base import BaseDeployment
from ..plugins.base import DeploymentInfo


class DummyDeploymentPlugin(BaseDeployment):
  """Deployment plugin for dummy models."""

  info = DeploymentInfo(
    name="dummy",
    title="Dummy Deployment",
    description="Dummy local deployment for testing",
  )

  def create_model(self, model_name, model_class, init_kwargs):
    # DummyModel takes no init-time configuration.
    return model_class(model_name=model_name)
