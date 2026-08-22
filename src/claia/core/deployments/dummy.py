"""
Dummy deployment.

Serves the dummy architecture; also the minimal reference for the
deployment seam.
"""

from typing import Any, Dict, Type

from .base import BaseDeployment
from ..decorators import deployment


@deployment
@deployment.name("dummy")
@deployment.title("Dummy Deployment")
@deployment.description("Dummy in-process deployment for testing")
class DummyDeployment(BaseDeployment):
  """Deployment for the dummy architecture."""

  def deploy(
    self,
    architecture_class: Type,
    model_name: str,
    init_kwargs: Dict[str, Any],
  ) -> Any:
    # The dummy architecture takes no init-time configuration.
    return architecture_class(model_name=model_name)
