"""
Message sequences — model-ready views of a conversation thread.

Conversation builds these from its active thread, filtering each
message's artifacts to what the model supports. Sequences are
conceptually read-only views (copies of messages).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Type, Union

from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import TextFormat


class MessageSequence:
  """Ordered thread messages with artifacts filtered for a model.

  ``messages`` are conversation ``Message`` copies. ``system`` is
  optional top-level instructions (from ``conversation.prompt``).
  """

  def __init__(
    self,
    messages: Optional[Sequence[Any]] = None,
    system: Optional[str] = None,
  ):
    self.messages: List[Any] = list(messages or [])
    self.system = system or None

  def __len__(self) -> int:
    return len(self.messages)

  def __iter__(self):
    return iter(self.messages)

  def to_dict(self) -> Dict[str, Any]:
    return {
      "system": self.system,
      "messages": [
        m.to_dict() if hasattr(m, "to_dict") else m
        for m in self.messages
      ],
      "sequence_type": type(self).__name__,
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> "MessageSequence":
    from .message import Message

    sequence_type = data.get("sequence_type", "MessageSequence")
    target: Type[MessageSequence] = cls
    if sequence_type == "MessageSequenceOrdered":
      target = MessageSequenceOrdered
    messages = []
    for item in data.get("messages", []):
      messages.append(item if not isinstance(item, dict) else Message.from_dict(item))
    return target(messages=messages, system=data.get("system"))


class MessageSequenceOrdered(MessageSequence):
  """Message sequence with user/assistant role alternation enforced.

  Consecutive same-role turns are merged. Leading assistant turns are
  dropped. Only user/assistant turns are kept.
  """

  def __init__(
    self,
    messages: Optional[Sequence[Any]] = None,
    system: Optional[str] = None,
  ):
    normalized = self._normalize(list(messages or []))
    super().__init__(messages=normalized, system=system)

  @staticmethod
  def _normalize(messages: List[Any]) -> List[Any]:
    from .message import Message
    from ...artifacts import TextArtifact

    filtered = [
      m for m in messages
      if getattr(m, "speaker", None) in (MessageRole.USER, MessageRole.ASSISTANT)
      or getattr(m, "role", None) in (MessageRole.USER, MessageRole.ASSISTANT)
    ]
    if not filtered:
      return []

    def _role(message) -> MessageRole:
      speaker = getattr(message, "speaker", None) or getattr(message, "role", None)
      return speaker if isinstance(speaker, MessageRole) else MessageRole(speaker)

    while filtered and _role(filtered[0]) == MessageRole.ASSISTANT:
      filtered.pop(0)
    if not filtered:
      return []

    merged: List[Any] = []
    for message in filtered:
      role = _role(message)
      if merged and _role(merged[-1]) == role:
        prev = merged[-1]
        prev_text = getattr(prev, "content", "") or ""
        next_text = getattr(message, "content", "") or ""
        non_text_prev = [
          a for a in (prev.artifacts or [])
          if not isinstance(a, TextArtifact)
        ]
        non_text_next = [
          a for a in (message.artifacts or [])
          if not isinstance(a, TextArtifact)
        ]
        if prev_text or next_text:
          text = TextArtifact.from_content(
            (prev_text + "\n" + next_text).strip(),
            name="merged",
            format=TextFormat.PLAIN,
          )
          prev.artifacts = [text, *non_text_prev, *non_text_next]
        else:
          prev.artifacts = list(prev.artifacts or []) + list(message.artifacts or [])
      else:
        # Copy into a fresh Message so merges don't mutate the source tree.
        if isinstance(message, Message):
          merged.append(Message.from_dict(message.to_dict()))
        else:
          merged.append(message)
    return merged
