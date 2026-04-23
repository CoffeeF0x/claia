"""
Abstract base class for tool-protocol plugins.

A protocol receives a tool name plus prepared parameters and is
responsible for executing the right command from the supplied catalog.
Different protocols can implement different invocation conventions
(e.g., direct local call, MCP, remote RPC).

Subclasses declare their metadata via a class-level ``info`` attribute
so plugin discovery does not have to instantiate the plugin.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict

from ...results import Result
from ...plugins.base import ProtocolInfo


class BaseProtocol(ABC):
  """Contract for tool-protocol plugins."""

  info: ClassVar[ProtocolInfo]

  def get_protocol_info(self) -> ProtocolInfo:
    """Return metadata describing this protocol.

    Default implementation returns the class-level ``info`` attribute.
    """
    return type(self).info

  @abstractmethod
  def execute(
    self,
    tool_name: str,
    parameters: Dict[str, Any],
    conversation,
    commands: Dict[str, Any],
    **kwargs,
  ) -> Result:
    """Execute ``tool_name`` and return a ``Result``."""
