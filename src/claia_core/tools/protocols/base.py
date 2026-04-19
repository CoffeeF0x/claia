"""
Abstract base class for tool-protocol plugins.

A protocol receives a tool name plus prepared parameters and is
responsible for executing the right command from the supplied catalog.
Different protocols can implement different invocation conventions
(e.g., direct local call, MCP, remote RPC).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from ...results import Result
from ...plugins.base import ProtocolInfo


class BaseProtocol(ABC):
  """Contract for tool-protocol plugins."""

  @abstractmethod
  def get_protocol_info(self) -> ProtocolInfo:
    """Return metadata describing this protocol."""

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
