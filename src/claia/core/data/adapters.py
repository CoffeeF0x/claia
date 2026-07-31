"""
Adapters between conversation-domain objects and IO artifacts.
"""

from __future__ import annotations

from typing import List, Sequence

from claia.core.data.artifacts import BaseArtifact, TextArtifact
from claia.core.data.models import Conversation
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import TextFormat


def conversation_to_artifacts(conversation: Conversation) -> List[BaseArtifact]:
  """Flatten the active conversation thread into an ordered artifact list.

  System prompt (if present) becomes the first text artifact. Each
  message on the active thread becomes a text artifact with speaker
  recorded in metadata.
  """
  artifacts: List[BaseArtifact] = []

  system = (conversation.prompt or {}).get("system") or ""
  if system.strip():
    artifacts.append(TextArtifact.from_content(
      system,
      name="system",
      format=TextFormat.PLAIN,
      metadata={"role": MessageRole.SYSTEM.value},
    ))

  for message in conversation.get_thread():
    artifacts.append(TextArtifact.from_content(
      message.content or "",
      name=f"message-{message.message_id[:8]}",
      format=TextFormat.PLAIN,
      metadata={
        "role": (
          message.speaker.value
          if hasattr(message.speaker, "value")
          else str(message.speaker)
        ),
        "message_id": message.message_id,
        "file_ids": list(message.file_ids or []),
      },
    ))

  return artifacts


def artifacts_text(artifacts: Sequence[BaseArtifact]) -> str:
  """Concatenate text artifact contents (for simple adapters)."""
  parts = []
  for artifact in artifacts:
    if isinstance(artifact, TextArtifact):
      parts.append(artifact.content)
  return "\n".join(parts)


def artifacts_to_conversation(artifacts: Sequence[BaseArtifact]) -> Conversation:
  """Rebuild a Conversation from text artifacts (role in metadata).

  Used by model implementations that still format provider payloads from
  a conversation tree. Non-text artifacts are skipped for now.
  """
  conversation = Conversation(title="from-artifacts")
  system_parts = []
  for artifact in artifacts:
    if not isinstance(artifact, TextArtifact):
      continue
    role = (artifact.metadata or {}).get("role", MessageRole.USER.value)
    if role == MessageRole.SYSTEM.value:
      system_parts.append(artifact.content)
    else:
      try:
        speaker = MessageRole(role)
      except ValueError:
        speaker = MessageRole.USER
      conversation.add_message(speaker, artifact.content)
  if system_parts:
    conversation.prompt = {"system": "\n".join(system_parts)}
  return conversation
