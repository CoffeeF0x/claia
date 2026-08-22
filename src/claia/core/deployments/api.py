"""
API deployment.

Serves hosted-API architectures (OpenAI, Anthropic, OpenRouter, …).
There is nothing to provision — deploying is constructing the
architecture's configured HTTP session — so this deployment is a
session factory plus the base metering relay.
"""

from .base import BaseDeployment
from ..decorators import deployment


@deployment
@deployment.name("api")
@deployment.title("API Deployment")
@deployment.description("Serve architectures that call hosted third-party APIs")
class APIDeployment(BaseDeployment):
  """Session factory + metering relay for hosted-API architectures."""

  api = True
