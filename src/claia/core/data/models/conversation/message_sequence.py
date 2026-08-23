"""
Message sequences — model-ready views of a conversation thread.

Conversation builds these from its active thread, filtering each
message's artifacts to what the model supports. Sequences are
conceptually read-only views (copies of messages). A generate-time
system message is a ``MessageRole.SYSTEM`` turn in ``messages``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Type

from ....enums.conversation import MessageRole
from ....enums.data import TextFormat


def _role(message) -> Optional[MessageRole]:
  role = getattr(message, "role", None)
  if role is None:
    return None
  return role if isinstance(role, MessageRole) else MessageRole(role)


def _prepend_system(messages: List[Any], system: Optional[str]) -> List[Any]:
  if system is None:
    return messages
  text = system.strip() if isinstance(system, str) else str(system).strip()
  if not text:
    return messages
  from .message import Message
  return [Message(role=MessageRole.SYSTEM, content=text), *messages]


class MessageSequence:
  """Ordered thread messages with artifacts filtered for a model.

  ``messages`` are conversation ``Message`` copies. A system message
  is a ``MessageRole.SYSTEM`` turn in that list, not a sidecar field.
  """

  def __init__(
    self,
    messages: Optional[Sequence[Any]] = None,
    system: Optional[str] = None,
  ):
    self.messages: List[Any] = _prepend_system(list(messages or []), system)

  def __len__(self) -> int:
    return len(self.messages)

  def __iter__(self):
    return iter(self.messages)

  @property
  def system(self) -> Optional[str]:
    """Concatenated text of ``SYSTEM`` turns, or None."""
    parts = []
    for message in self.messages:
      if _role(message) != MessageRole.SYSTEM:
        continue
      text = getattr(message, "content", None)
      if text and str(text).strip():
        parts.append(str(text).strip())
    return "\n\n".join(parts) if parts else None

  def to_dict(self) -> Dict[str, Any]:
    return {
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

  Consecutive same-role user/assistant turns are merged. Leading
  assistant and utility turns are dropped. ``SYSTEM`` turns stay at
  the front. ``UTILITY`` turns (tool results) are valid between
  assistant turns and are never merged with a neighbour.
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

    systems = [m for m in messages if _role(m) == MessageRole.SYSTEM]
    filtered = [
      m for m in messages
      if _role(m) in (MessageRole.USER, MessageRole.ASSISTANT, MessageRole.UTILITY)
    ]
    if not filtered:
      return list(systems)

    while filtered and _role(filtered[0]) in (MessageRole.ASSISTANT, MessageRole.UTILITY):
      filtered.pop(0)
    if not filtered:
      return list(systems)

    merged: List[Any] = []
    for message in filtered:
      role = _role(message)
      if role == MessageRole.UTILITY:
        if isinstance(message, Message):
          merged.append(Message.from_dict(message.to_dict()))
        else:
          merged.append(message)
        continue
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
        if isinstance(message, Message):
          merged.append(Message.from_dict(message.to_dict()))
        else:
          merged.append(message)
    return list(systems) + merged
