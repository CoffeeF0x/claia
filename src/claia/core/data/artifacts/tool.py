"""Tool artifact — tool-call / tool-result payload on a message."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from claia.core.enums.data import ApplicationFormat, MediaType

from .base import BaseArtifact


class ToolArtifact(BaseArtifact):
  """Structured tool call or tool result carried on a message.

  Replaces ad-hoc tool response text embedded in assistant content.
  ``payload`` is the structured body (arguments or result); ``tool_name``
  and optional ``call_id`` identify the invocation.
  """

  def __init__(
    self,
    name: str = "tool",
    tool_name: str = "",
    call_id: Optional[str] = None,
    payload: Optional[Any] = None,
    is_result: bool = False,
    **kwargs,
  ):
    kwargs.pop("type", None)
    kwargs.pop("format", None)
    super().__init__(
      type=MediaType.APPLICATION,
      format=ApplicationFormat.JSON,
      name=name,
      **kwargs,
    )
    self.tool_name = tool_name
    self.call_id = call_id
    self.is_result = is_result
    self.metadata["tool_name"] = tool_name
    if call_id is not None:
      self.metadata["call_id"] = call_id
    self.metadata["is_result"] = is_result
    if payload is not None:
      self.set_content(payload)

  def load_content(self) -> Any:
    if self._content_loaded:
      return self._content
    return None

  def set_content(self, payload: Any) -> None:
    self._content = payload
    self._content_loaded = True
    encoded = json.dumps(payload, default=str).encode("utf-8")
    self.size = len(encoded)
    self.updated_at = time.time()

  @property
  def content(self) -> Any:
    return self.load_content()

  def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()
    data["artifact_type"] = "tool"
    data["tool_name"] = self.tool_name
    data["call_id"] = self.call_id
    data["is_result"] = self.is_result
    if self._content_loaded:
      data["payload"] = self._content
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> ToolArtifact:
    artifact = cls(
      name=data.get("name", "tool"),
      tool_name=data.get("tool_name") or data.get("metadata", {}).get("tool_name", ""),
      call_id=data.get("call_id") or data.get("metadata", {}).get("call_id"),
      is_result=bool(data.get("is_result") or data.get("metadata", {}).get("is_result")),
      guid=data.get("guid") or data.get("id"),
      original=data.get("original"),
      size=data.get("size", 0),
      metadata=data.get("metadata", {}),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
    )
    if "payload" in data:
      artifact.set_content(data["payload"])
    return artifact

  @classmethod
  def from_call(
    cls,
    tool_name: str,
    payload: Any,
    call_id: Optional[str] = None,
    **kwargs,
  ) -> ToolArtifact:
    return cls(
      name=kwargs.pop("name", f"tool-call-{tool_name}"),
      tool_name=tool_name,
      call_id=call_id,
      payload=payload,
      is_result=False,
      **kwargs,
    )

  @classmethod
  def from_result(
    cls,
    tool_name: str,
    payload: Any,
    call_id: Optional[str] = None,
    **kwargs,
  ) -> ToolArtifact:
    return cls(
      name=kwargs.pop("name", f"tool-result-{tool_name}"),
      tool_name=tool_name,
      call_id=call_id,
      payload=payload,
      is_result=True,
      **kwargs,
    )
