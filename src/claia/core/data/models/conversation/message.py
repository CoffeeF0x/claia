"""
Message data model for conversations.

Messages are wrappers around an ordered list of artifacts. A thin
``content`` property reads/writes the primary ``TextArtifact`` for
streaming convenience.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
import uuid
import threading

from ....enums.conversation import MessageRole
from ....enums.data import TextFormat
from ....enums.parser import TagType


def _artifact_from_dict(data: Dict[str, Any]):
  """Rehydrate an artifact dict into a typed instance."""
  from ...artifacts import (
    AudioArtifact,
    FileArtifact,
    ImageArtifact,
    LinkArtifact,
    RawArtifact,
    TextArtifact,
    ToolArtifact,
  )
  atype = data.get("artifact_type")
  if atype == "tool" or data.get("tool_name") is not None:
    return ToolArtifact.from_dict(data)
  if atype == "image" or data.get("type") == "image":
    return ImageArtifact.from_dict(data)
  if atype == "audio" or data.get("type") == "audio":
    return AudioArtifact.from_dict(data)
  if atype == "link" or data.get("uri") is not None:
    return LinkArtifact.from_dict(data)
  if atype == "file":
    return FileArtifact.from_dict(data)
  if atype == "raw" or data.get("format") == "octet-stream":
    return RawArtifact.from_dict(data)
  return TextArtifact.from_dict(data)


########################################################################
#                               MESSAGE                                #
########################################################################
class Message:
  """
  A turn in a conversation tree.

  Payload lives in ``artifacts`` (ordered). ``content`` is a convenience
  view over the primary ``TextArtifact``.
  """

  def __init__(
    self,
    role: MessageRole,
    content: str = "",
    message_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    artifacts: Optional[List[Any]] = None,
    created_at: Optional[float] = None,
    updated_at: Optional[float] = None,
    tag_type: Optional[TagType] = None,
    source_message_id: Optional[str] = None,
    start_index: Optional[int] = None,
    end_index: Optional[int] = None,
    attributes: Optional[Dict[str, str]] = None,
  ):
    from ...artifacts import BaseArtifact, TextArtifact

    self.message_id = message_id or str(uuid.uuid4())
    self.parent_id = parent_id
    self.role = role if isinstance(role, MessageRole) else MessageRole(role)
    self.created_at = created_at or time.time()
    self.updated_at = updated_at or self.created_at

    if tag_type is not None and not isinstance(tag_type, TagType):
      tag_type = TagType(tag_type)
    self.tag_type: Optional[TagType] = tag_type
    self.source_message_id: Optional[str] = source_message_id
    self.start_index: Optional[int] = start_index
    self.end_index: Optional[int] = end_index
    self.attributes: Dict[str, str] = dict(attributes) if attributes else {}

    self.artifacts: List[BaseArtifact] = []
    if artifacts:
      for item in artifacts:
        if isinstance(item, dict):
          self.artifacts.append(_artifact_from_dict(item))
        else:
          self.artifacts.append(item)
    elif content:
      self.artifacts.append(TextArtifact.from_content(
        content,
        name=f"message-{self.message_id[:8]}",
        format=TextFormat.PLAIN,
      ))

    self._content_lock = threading.Lock()

  def _primary_text_artifact(self):
    from ...artifacts import TextArtifact
    for artifact in self.artifacts:
      if isinstance(artifact, TextArtifact):
        return artifact
    return None

  def _ensure_primary_text(self):
    from ...artifacts import TextArtifact
    primary = self._primary_text_artifact()
    if primary is None:
      primary = TextArtifact.from_content(
        "",
        name=f"message-{self.message_id[:8]}",
        format=TextFormat.PLAIN,
      )
      self.artifacts.insert(0, primary)
    return primary

  @property
  def content(self) -> str:
    """Primary text payload (empty string if none)."""
    primary = self._primary_text_artifact()
    return primary.content if primary is not None else ""

  @content.setter
  def content(self, value: str) -> None:
    primary = self._ensure_primary_text()
    primary.set_content(value or "")
    self.updated_at = time.time()

  def add_artifact(self, artifact) -> None:
    """Append an artifact to this message."""
    self.artifacts.append(artifact)
    self.updated_at = time.time()

  def tool_result_artifacts(self) -> List[Any]:
    """Return ``ToolArtifact`` results attached to this message."""
    from ...artifacts import ToolArtifact
    return [
      a for a in self.artifacts
      if isinstance(a, ToolArtifact) and a.is_result
    ]

  def copy_with_artifacts(self, artifacts: List[Any]) -> "Message":
    """Return a copy of this message carrying ``artifacts`` only."""
    data = self.to_dict()
    data["artifacts"] = [
      a.to_dict() if hasattr(a, "to_dict") else a for a in artifacts
    ]
    return Message.from_dict(data)

  def is_utility(self) -> bool:
    """Return ``True`` if this message is a parsed-tag sibling."""
    return self.role == MessageRole.UTILITY

  def to_dict(self) -> Dict[str, Any]:
    data: Dict[str, Any] = {
      "message_id": self.message_id,
      "parent_id": self.parent_id,
      "role": self.role.value,
      "artifacts": [a.to_dict() for a in self.artifacts],
      "created_at": self.created_at,
      "updated_at": self.updated_at,
    }
    if self.tag_type is not None:
      data["tag_type"] = self.tag_type.value
    if self.source_message_id is not None:
      data["source_message_id"] = self.source_message_id
    if self.start_index is not None:
      data["start_index"] = self.start_index
    if self.end_index is not None:
      data["end_index"] = self.end_index
    if self.attributes:
      data["attributes"] = dict(self.attributes)
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> Message:
    artifacts = data.get("artifacts")
    content = ""
    if not artifacts and data.get("content"):
      # API convenience when only a text string is present.
      content = data.get("content", "")
    return cls(
      role=data.get("role") or data.get("speaker") or MessageRole.USER.value,
      content=content,
      message_id=data.get("message_id"),
      parent_id=data.get("parent_id"),
      artifacts=artifacts,
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
      tag_type=data.get("tag_type"),
      source_message_id=data.get("source_message_id"),
      start_index=data.get("start_index"),
      end_index=data.get("end_index"),
      attributes=data.get("attributes"),
    )

  def safe_update_content(self, new_content: str) -> None:
    with self._content_lock:
      self.content = new_content

  def safe_append_content(self, chunk: str) -> None:
    with self._content_lock:
      self.content = self.content + chunk

  def safe_replace_substring(self, start: int, end: int, replacement: str) -> bool:
    with self._content_lock:
      current = self.content
      if 0 <= start < end <= len(current):
        self.content = current[:start] + replacement + current[end:]
        return True
      return False

  def safe_get_content(self) -> str:
    with self._content_lock:
      return self.content
