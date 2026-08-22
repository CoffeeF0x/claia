"""
Transformers deployment.

Serves in-process architectures that hold model weights (HF
transformers, diffusers pipelines, TTS backends). Deploying constructs
the architecture instance — which is where weight loading happens —
and teardown releases the weights.
"""

from typing import Any, Dict, Type

from .base import BaseDeployment
from ..decorators import deployment


@deployment
@deployment.name("transformers")
@deployment.title("Transformers Deployment")
@deployment.description("Serve in-process weight-holding architectures (transformers, diffusers, TTS)")
class TransformersDeployment(BaseDeployment):
  """In-process weight loading and release for local architectures."""

  def deploy(
    self,
    architecture_class: Type,
    model_name: str,
    init_kwargs: Dict[str, Any],
  ) -> Any:
    ctor_kwargs = dict(init_kwargs)
    device = ctor_kwargs.pop("device", "cpu")
    model_path = ctor_kwargs.pop("model_path", None)
    defer_loading = ctor_kwargs.pop("defer_loading", False)
    return architecture_class(
      model_name=model_name,
      model_path=model_path,
      defer_loading=defer_loading,
      device=device,
      **ctor_kwargs,
    )

  def teardown(self, instance: Any) -> None:
    if hasattr(instance, "unload"):
      instance.unload()
