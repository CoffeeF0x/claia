"""
Remote deployment method plugin.

This deployment method handles remote models that run on remote servers,
cloud VMs, or other distributed systems.
"""

from typing import Any, Dict, Type

from .base import BaseDeployment
from ..results import DeploymentError, Result
from ..plugins.base import DeploymentInfo


class RemoteDeploymentPlugin(BaseDeployment):
  """Remote deployment method plugin for distributed models."""

  info = DeploymentInfo(
    name="remote",
    title="Remote Deployment",
    description="Deploy models on remote servers or cloud VMs",
  )

  def create_model(
    self,
    model_name: str,
    model_class: Type,
    init_kwargs: Dict[str, Any],
  ) -> Any:
    server_url = (
      init_kwargs.get("server_url")
      or init_kwargs.get("remote_url")
      or init_kwargs.get("base_url")
    )
    if not server_url:
      raise DeploymentError(f"Remote server URL required for model {model_name}")

    ctor_kwargs = dict(init_kwargs)
    ctor_kwargs.setdefault("server_url", server_url)
    ctor_kwargs.setdefault("base_url", server_url)

    model_instance = model_class(model_name=model_name, **ctor_kwargs)

    if hasattr(model_instance, "test_connection"):
      conn_result = model_instance.test_connection()
      if isinstance(conn_result, Result) and conn_result.is_error():
        raise DeploymentError(conn_result.get_message())

    return model_instance
