"""
Utility functions for the CLAIA CLI.
"""

import logging
from typing import Optional

from ..core.data.models import Conversation


logger = logging.getLogger(__name__)


def active_system(settings) -> Optional[str]:
  """Return the CLI's active prompt text, or None if none is set."""
  prompt = getattr(settings, "active_prompt", None)
  content = getattr(prompt, "content", None) if prompt else None
  if isinstance(content, str) and content.strip():
    return content.strip()
  return None


def ensure_active_conversation(settings) -> Conversation:
  """Return the active conversation, creating one only when needed."""
  conversation = getattr(settings, "active_conversation", None)
  if conversation is None:
    conversation = Conversation()
    settings.active_conversation = conversation
  return conversation
