"""
Pluggy hookspecs for tool-protocol plugins.

These specs mirror ``BaseProtocol`` in
``claia.core.tools.protocols.base`` (see the ExoFox docs repo
``claia/overview.md`` Decisions). The old pre-overhaul ``execute``
signature lives under
``claia.core.tools.protocols._legacy`` and is not surfaced through
pluggy; legacy plugins must migrate to the new contract before they
can register.
"""

from typing import List

import pluggy

from ...core.plugins.base import ProtocolInfo, ToolReference
from ...core.results import Result


hookspec = pluggy.HookspecMarker("claia_tool_protocols")


class ProtocolHooks:
  """Hook specifications for tool-protocol plugins."""

  @hookspec
  def get_protocol_info(self) -> ProtocolInfo:
    """Return metadata describing this protocol."""

  @hookspec
  def start(self) -> None:
    """Open sessions, validate config, warm caches. No-op by default."""

  @hookspec
  def stop(self) -> None:
    """Close sessions, release resources. No-op by default."""

  @hookspec
  def refresh(self) -> None:
    """Re-fetch dynamic tool inventories. No-op by default."""

  @hookspec
  def get_tool_references(self) -> List[ToolReference]:
    """Return the tool inventory this protocol owns."""

  @hookspec
  def execute(
    self,
    qualified_name: str,
    raw_payload: str,
    conversation,
    **kwargs,
  ) -> Result:
    """Execute ``qualified_name`` with the given raw payload.

    ``raw_payload`` is the tag body as emitted by the parser; the
    protocol is responsible for decoding it into call parameters.
    """


__all__ = ["ProtocolHooks", "ProtocolInfo", "ToolReference"]
