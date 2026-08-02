"""
Message sequences — model-ready views of a conversation thread.

Conversation exports a structural active-thread view; deployments
translate that into a ``MessageSequence`` (or ordered variant) filtered
to the model's supported artifact types.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ArtifactType, SequenceKind, TextFormat


class SequenceMessage:
  """One turn in a message sequence (role + ordered artifacts)."""

  def __init__(
    self,
    role: Union[MessageRole, str],
    artifacts: Optional[List[Any]] = None,
    message_id: Optional[str] = None,
  ):
    self.role = role if isinstance(role, MessageRole) else MessageRole(role)
    self.artifacts: List[Any] = list(artifacts or [])
    self.message_id = message_id

  @property
  def content(self) -> str:
    """Primary text payload (empty string if none)."""
    from ...artifacts import TextArtifact
    for artifact in self.artifacts:
      if isinstance(artifact, TextArtifact):
        return artifact.content or ""
    return ""

  def text_parts(self) -> List[str]:
    from ...artifacts import TextArtifact
    return [
      a.content for a in self.artifacts
      if isinstance(a, TextArtifact) and a.content
    ]

  def to_dict(self) -> Dict[str, Any]:
    return {
      "role": self.role.value,
      "message_id": self.message_id,
      "artifacts": [
        a.to_dict() if hasattr(a, "to_dict") else a
        for a in self.artifacts
      ],
      "content": self.content,
    }


class MessageSequence:
  """Ordered active-thread turns filtered for a model.

  ``system`` is optional top-level instructions (not a turn).
  ``kind`` records how the sequence was shaped (NONE / MESSAGE / ORDERED).
  """

  def __init__(
    self,
    messages: Optional[Sequence[SequenceMessage]] = None,
    system: Optional[str] = None,
    kind: SequenceKind = SequenceKind.MESSAGE,
  ):
    self.messages: List[SequenceMessage] = list(messages or [])
    self.system = system or None
    self.kind = kind if isinstance(kind, SequenceKind) else SequenceKind(kind)

  def __len__(self) -> int:
    return len(self.messages)

  def __iter__(self):
    return iter(self.messages)

  def chat_turns(self) -> List[SequenceMessage]:
    """User/assistant turns only (skip system/utility)."""
    return [
      m for m in self.messages
      if m.role in (MessageRole.USER, MessageRole.ASSISTANT)
    ]

  def latest_user_text(self) -> str:
    """Text from the most recent user turn."""
    for message in reversed(self.messages):
      if message.role == MessageRole.USER and message.content:
        return message.content
    return ""

  def to_chat_dicts(
    self,
    *,
    include_system: bool = False,
    role_map: Optional[Dict[MessageRole, str]] = None,
  ) -> List[Dict[str, str]]:
    """Provider-style ``[{role, content}, …]`` from text artifacts."""
    roles = role_map or {
      MessageRole.USER: "user",
      MessageRole.ASSISTANT: "assistant",
      MessageRole.SYSTEM: "system",
    }
    out: List[Dict[str, str]] = []
    if include_system and self.system:
      out.append({"role": roles.get(MessageRole.SYSTEM, "system"), "content": self.system})
    for message in self.chat_turns():
      if not message.content:
        continue
      out.append({
        "role": roles.get(message.role, message.role.value),
        "content": message.content,
      })
    return out

  def to_prompt_lines(
    self,
    *,
    include_system: bool = True,
    assistant_suffix: str = "Assistant:",
  ) -> str:
    """Simple text prompt for local/causal models."""
    parts: List[str] = []
    if include_system and self.system:
      parts.append(f"System: {self.system}")
    for message in self.messages:
      if message.role == MessageRole.SYSTEM:
        parts.append(f"System: {message.content}")
      elif message.role == MessageRole.USER:
        parts.append(f"User: {message.content}")
      elif message.role == MessageRole.ASSISTANT:
        parts.append(f"Assistant: {message.content}")
    if assistant_suffix:
      parts.append(assistant_suffix)
    return "\n".join(parts)

  @classmethod
  def flatten(
    cls,
    messages: Sequence[SequenceMessage],
    system: Optional[str] = None,
  ) -> "MessageSequence":
    """Collapse turns into a single user turn (``SequenceKind.NONE``)."""
    from ...artifacts import TextArtifact
    texts = []
    if system:
      texts.append(system)
    for message in messages:
      if message.content:
        texts.append(message.content)
    blob = "\n".join(texts)
    turn = SequenceMessage(
      role=MessageRole.USER,
      artifacts=[TextArtifact.from_content(
        blob, name="flat", format=TextFormat.PLAIN,
      )] if blob else [],
    )
    return cls(messages=[turn] if turn.artifacts else [], system=None, kind=SequenceKind.NONE)


class OrderedMessageSequence(MessageSequence):
  """Message sequence with Anthropic-style role alternation.

  Consecutive same-role turns are merged (text concatenated). Leading
  assistant turns are dropped; an empty trailing user turn is not
  invented — callers must ensure a legal end state for their API.
  """

  def __init__(
    self,
    messages: Optional[Sequence[SequenceMessage]] = None,
    system: Optional[str] = None,
    kind: SequenceKind = SequenceKind.ORDERED,
  ):
    normalized = self._normalize(list(messages or []))
    super().__init__(messages=normalized, system=system, kind=SequenceKind.ORDERED)

  @staticmethod
  def _normalize(messages: List[SequenceMessage]) -> List[SequenceMessage]:
    from ...artifacts import TextArtifact

    # Keep only user/assistant
    filtered = [
      m for m in messages
      if m.role in (MessageRole.USER, MessageRole.ASSISTANT)
    ]
    if not filtered:
      return []

    # Drop leading assistants
    while filtered and filtered[0].role == MessageRole.ASSISTANT:
      filtered.pop(0)
    if not filtered:
      return []

    merged: List[SequenceMessage] = []
    for message in filtered:
      if merged and merged[-1].role == message.role:
        prev = merged[-1]
        combined = list(prev.artifacts)
        # Prefer concatenating text when both sides are text-only merges
        prev_text = prev.content
        next_text = message.content
        if prev_text is not None and next_text:
          # Rebuild primary text; keep non-text artifacts from both
          non_text_prev = [
            a for a in prev.artifacts
            if not isinstance(a, TextArtifact)
          ]
          non_text_next = [
            a for a in message.artifacts
            if not isinstance(a, TextArtifact)
          ]
          text = TextArtifact.from_content(
            (prev_text + "\n" + next_text).strip(),
            name="merged",
            format=TextFormat.PLAIN,
          )
          prev.artifacts = [text, *non_text_prev, *non_text_next]
        else:
          prev.artifacts = combined + list(message.artifacts)
      else:
        merged.append(SequenceMessage(
          role=message.role,
          artifacts=list(message.artifacts),
          message_id=message.message_id,
        ))
    return merged


def filter_artifacts(
  artifacts: Iterable[Any],
  supported: Sequence[ArtifactType],
) -> List[Any]:
  """Keep artifacts whose ``ArtifactType`` is in ``supported``."""
  allowed = set(supported)
  out = []
  for artifact in artifacts:
    if ArtifactType.from_artifact(artifact) in allowed:
      out.append(artifact)
  return out
