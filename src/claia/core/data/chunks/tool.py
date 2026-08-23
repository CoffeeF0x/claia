"""Tool chunk — streamed native tool call."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...enums.data import ApplicationFormat, MediaType

from .base import BaseChunk


class ToolChunk(BaseChunk):
  """A tool call produced by the architecture (NATIVE mode).

  Fields match ``ToolArtifact.from_call``: ``tool_name``, ``payload``
  (arguments), optional ``call_id``. A tool call is model content.
  """

  def __init__(
    self,
    tool_name: str = "",
    payload: Optional[Any] = None,
    call_id: Optional[str] = None,
    name: str = "tool",
    metadata: Optional[Dict[str, Any]] = None,
  ):
    metadata = dict(metadata or {})
    metadata["tool_name"] = tool_name
    if call_id is not None:
      metadata["call_id"] = call_id
    super().__init__(
      type=MediaType.APPLICATION,
      format=ApplicationFormat.JSON,
      name=name or f"tool-call-{tool_name}",
      metadata=metadata,
      data=payload,
    )
    self.tool_name = tool_name
    self.call_id = call_id
    self.payload = payload
