"""
API deployment method plugin.

This deployment method handles API-based models that make remote calls
to services like OpenAI, Anthropic, etc.
"""

from .base import BaseDeployment
from ..plugins.base import DeploymentInfo


class APIDeploymentPlugin(BaseDeployment):
  """API deployment method plugin for remote API-based models."""

  info = DeploymentInfo(
    name="api",
    title="API Deployment",
    description="Deploy models via external API services (OpenAI, Anthropic, etc.)",
  )
