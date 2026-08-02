"""
Message data model for conversations.

Messages represent individual turns in a conversation. Each message
carries an ordered list of artifacts (text, image, tool, …). A thin
``content`` property reads/writes the primary text artifact so
streaming and legacy callers keep working.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import json
import time
import uuid
import re
import threading

from ....enums.conversation import MessageRole
from ....enums.data import TextFormat
from ....parser.types import TagType


########################################################################
#                              CONSTANTS                               #
########################################################################
LEFT_ARG_WRAPPER = "{"
RIGHT_ARG_WRAPPER = "}"


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


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
  view over the primary ``TextArtifact``. Utility-message metadata
  (tag_type, source offsets, …) is unchanged from the tools overhaul.
  """

  def __init__(
    self,
    speaker: MessageRole,
    content: str = "",
    message_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    file_ids: Optional[List[str]] = None,
    artifacts: Optional[List[Any]] = None,
    created_at: Optional[float] = None,
    updated_at: Optional[float] = None,
    inline_args: Optional[Dict[str, Any]] = None,
    tag_type: Optional[TagType] = None,
    source_message_id: Optional[str] = None,
    start_index: Optional[int] = None,
    end_index: Optional[int] = None,
    attributes: Optional[Dict[str, str]] = None,
  ):
    from ...artifacts import BaseArtifact, TextArtifact

    self.message_id = message_id or str(uuid.uuid4())
    self.parent_id = parent_id
    self.speaker = speaker if isinstance(speaker, MessageRole) else MessageRole(speaker)
    self.created_at = created_at or time.time()
    self.updated_at = updated_at or self.created_at
    self.inline_args = inline_args or {}

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

    if file_ids is not None:
      self.file_ids = file_ids
    else:
      primary = self._primary_text_artifact()
      self.file_ids = [a.id for a in self.artifacts if a is not primary]

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
    """Append an artifact and refresh transitional file_ids."""
    self.artifacts.append(artifact)
    primary = self._primary_text_artifact()
    self.file_ids = [a.id for a in self.artifacts if a is not primary]
    self.updated_at = time.time()

  def is_utility(self) -> bool:
    """Return ``True`` if this message is a parsed-tag sibling."""
    return self.speaker == MessageRole.UTILITY

  def to_dict(self) -> Dict[str, Any]:
    data: Dict[str, Any] = {
      "message_id": self.message_id,
      "parent_id": self.parent_id,
      "speaker": self.speaker.value,
      "content": self.content,
      "file_ids": self.file_ids,
      "artifacts": [a.to_dict() for a in self.artifacts],
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      "inline_args": self.inline_args,
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
    return cls(
      speaker=data.get("speaker", MessageRole.USER.value),
      content=data.get("content", "") if not data.get("artifacts") else "",
      message_id=data.get("message_id"),
      parent_id=data.get("parent_id"),
      file_ids=data.get("file_ids", []),
      artifacts=data.get("artifacts"),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
      inline_args=data.get("inline_args", {}) or data.get("query_args", {}),
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

  def extract_inline_args(
    self,
    left_wrapper: str = LEFT_ARG_WRAPPER,
    right_wrapper: str = RIGHT_ARG_WRAPPER,
  ) -> str:
    updated_content = self.content
    arg_pattern = re.compile(
      f"\\{left_wrapper}([^{left_wrapper}{right_wrapper}]+?)\\{right_wrapper}"
    )
    matches = arg_pattern.finditer(self.content)

    for match in matches:
      arg_text = match.group(1)
      full_match = match.group(0)
      try:
        if "=" in arg_text:
          key, value = arg_text.split("=", 1)
          self.inline_args[key.strip()] = self._convert_value_type(value.strip())
        elif ":" in arg_text:
          key, value = arg_text.split(":", 1)
          self.inline_args[key.strip()] = self._convert_value_type(value.strip())
        elif arg_text.startswith("--") and " " in arg_text:
          parts = arg_text.split(" ", 1)
          key = parts[0][2:].strip()
          value = parts[1].strip()
          if key and value:
            self.inline_args[key] = self._convert_value_type(value)
        elif arg_text.startswith("--"):
          key = arg_text[2:].strip()
          if key:
            self.inline_args[key] = True
        else:
          key = arg_text.strip()
          if key:
            self.inline_args[key] = True
        updated_content = updated_content.replace(full_match, "", 1)
      except Exception as e:
        logger.warning(f"Failed to parse argument '{arg_text}': {e}")

    self.content = updated_content.strip()
    return self.content

  def _convert_value_type(self, value: str) -> Any:
    if value.lower() == "true":
      return True
    if value.lower() == "false":
      return False
    if value.isdigit():
      return int(value)
    if re.match(r"^-?\d+(\.\d+)?$", value):
      return float(value)
    if (
      (value.startswith("[") and value.endswith("]"))
      or (value.startswith("{") and value.endswith("}"))
    ):
      try:
        return json.loads(value)
      except json.JSONDecodeError:
        pass
    return value

  def get_inline_args(self) -> Dict[str, Any]:
    return self.inline_args.copy()

  def has_inline_args(self) -> bool:
    return bool(self.inline_args)
