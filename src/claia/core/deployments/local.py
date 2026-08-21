"""
Local deployment method plugin.

This deployment method handles local models that run on the user's machine,
typically transformer models loaded via HuggingFace transformers.
"""

from typing import Any, Dict, Type

from .base import BaseDeployment
from ..decorators import deployment


@deployment
@deployment.name("local")
@deployment.title("Local Deployment")
@deployment.description("Deploy models locally using transformers/torch")
class LocalDeploymentPlugin(BaseDeployment):
  """Local deployment method plugin for transformer-based models."""

  def create_model(
    self,
    model_name: str,
    model_class: Type,
    init_kwargs: Dict[str, Any],
  ) -> Any:
    ctor_kwargs = dict(init_kwargs)
    device = ctor_kwargs.pop("device", "cpu")
    model_path = ctor_kwargs.pop("model_path", None)
    defer_loading = ctor_kwargs.pop("defer_loading", False)
    return model_class(
      model_name=model_name,
      model_path=model_path,
      defer_loading=defer_loading,
      device=device,
      **ctor_kwargs,
    )
