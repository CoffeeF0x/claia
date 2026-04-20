"""
Pluggy hookspecs for tool-protocol plugins.

These specs mirror ``BaseProtocol`` in
``claia.core.tools.protocols.base``.
"""

import pluggy
from typing import Any, Dict

from claia.core.results import Result
from claia.core.plugins.base import ProtocolInfo


hookspec = pluggy.HookspecMarker("claia_tool_protocols")


class ProtocolHooks:
  """Hook specifications for tool-protocol plugins."""

  @hookspec
  def get_protocol_info(self) -> ProtocolInfo:
    """Return metadata describing this protocol."""

  @hookspec
  def execute(
    self,
    tool_name: str,
    parameters: Dict[str, Any],
    conversation,
    commands: Dict[str, Any],
    **kwargs,
  ) -> Result:
    """Execute ``tool_name`` and return a ``Result``."""


__all__ = ["ProtocolHooks", "ProtocolInfo"]
