"""
Utility functions for the CLAIA CLI.
"""

import logging
from typing import List, Optional

from ..core.data.models import Conversation
from ..core.enums.conversation import MessageRole
from ..core.enums.model import SourcePreference
from ..core.parser import TagSpec, resolve_tag_specs
from ..framework.task import Task


########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_AGENT = "simple"


logger = logging.getLogger(__name__)


########################################################################
#                              FUNCTIONS                               #
########################################################################
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


def prepare_query_task(
  settings, text: str, conversation: Optional[Conversation] = None,
) -> Task:
  """Build a query task for ``text`` from the active settings.

  Records the user turn on ``conversation`` — the active one by
  default (created when missing), or an explicit one so the TUI can
  submit into tracks that are not currently active — and assembles
  the task the same way for every host path (one-shot query and TUI
  submit).
  """
  if conversation is None:
    conversation = ensure_active_conversation(settings)

  if not settings.active_agent:
    settings.active_agent = settings.default_agent or DEFAULT_AGENT

  conversation.add_message(MessageRole.USER, text)

  parameters = {
    "source_preference": SourcePreference.ANY,
    "model_id": settings.active_model,
    **settings.get_user_kwargs(),
  }
  system = active_system(settings)
  if system:
    parameters["system"] = system

  return Task(
    agent_type=settings.active_agent,
    conversation=conversation,
    parameters=parameters,
  )


def stream_tag_specs(registry, model_id: Optional[str]) -> List[TagSpec]:
  """Mirror the agent's tag-spec resolution: exact id, else defaults."""
  definitions = registry.get_supported_models()
  model_def = None
  if isinstance(definitions, dict) and model_id in definitions:
    model_def = definitions[model_id]
  return resolve_tag_specs(model_def)
