"""
Abstract base class for tool protocols.

A *protocol* is a tool-execution backend. It owns its own tool
inventory (returned via :meth:`BaseProtocol.get_tool_references`) and
its own dispatch logic (:meth:`BaseProtocol.execute`). The registry
holds no callables of its own; it assembles a unified index of
``ToolReference`` objects across all loaded protocols and routes
``execute_tool`` calls back to the owning protocol.

See the ExoFox docs repo ``claia/overview.md`` Decisions for the
rationale.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, List

from ...plugins.base import ProtocolInfo, ToolReference
from ...results import Result


class BaseProtocol(ABC):
  """Contract for tool-protocol plugins (overhaul contract).

  Subclasses declare their metadata via a class-level ``info`` attribute
  so plugin discovery does not have to instantiate the plugin.
  Lifecycle hooks (:meth:`start`, :meth:`stop`, :meth:`refresh`) carry
  default no-op implementations; override them when a protocol needs
  to manage external sessions (MCP, remote RPC, etc.).
  """

  info: ClassVar[ProtocolInfo]

  def start(self) -> None:
    """Open sessions, validate config, warm caches.

    Called by the framework after the plugin is instantiated and
    registered. Default implementation is a no-op. Override to manage
    external resources (e.g. open MCP sessions, probe a remote service).
    """

  def stop(self) -> None:
    """Close sessions, release resources.

    Called by the framework during teardown. Default implementation is
    a no-op. Override to tear down anything set up in :meth:`start`.
    """

  def refresh(self) -> None:
    """Re-fetch dynamic tool inventories.

    Called when an external inventory source signals that tools may
    have changed (e.g. MCP ``notifications/tools/list_changed``).
    Default implementation is a no-op; static protocols need no
    refresh.
    """

  @abstractmethod
  def get_tool_references(self) -> List[ToolReference]:
    """Return the tool inventory this protocol owns.

    Called by the registry to assemble its unified tool index.
    Qualified names are namespaced (e.g. ``"module.tool"`` for
    native tools, ``"mcp.<server>.<tool>"`` for MCP-sourced tools).
    """

  @abstractmethod
  def execute(
    self,
    qualified_name: str,
    raw_payload: str,
    conversation,
    **kwargs,
  ) -> Result:
    """Execute the named tool and return a ``Result``.

    Arguments:
      qualified_name: the fully-namespaced tool name from the
        ``ToolReference`` returned by :meth:`get_tool_references`.
      raw_payload: the raw content string from the parser — the text
        between a tag's open and close tokens. The protocol is
        responsible for decoding this into call parameters in whatever
        format that protocol uses (JSON for the simple protocol,
        something else for MCP, etc.). The registry is payload-agnostic.
      conversation: the active ``Conversation`` object for tools that
        need to read history, attach artifacts, or append messages.
      **kwargs: cross-cutting knobs (settings, cancellation tokens,
        tool-context injectables). Unknown kwargs are tolerated.
    """


__all__ = ["BaseProtocol"]
