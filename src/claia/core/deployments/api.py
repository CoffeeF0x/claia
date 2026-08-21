"""
API deployment.

This deployment handles API-based models that make remote calls
to services like OpenAI, Anthropic, etc.
"""

from .base import BaseDeployment
from ..decorators import deployment


@deployment
@deployment.name("api")
@deployment.title("API Deployment")
@deployment.description("Deploy models via external API services (OpenAI, Anthropic, etc.)")
class APIDeployment(BaseDeployment):
  """API deployment for remote API-based models."""
