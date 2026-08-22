"""CLI conversations are created only when a query needs one."""

from types import SimpleNamespace

from claia.cli.commands.conversation import ConversationCommand
from claia.cli.utils import ensure_active_conversation
from claia.core.data.models import Conversation


def test_ensure_creates_once_and_reuses():
  settings = SimpleNamespace(active_conversation=None)

  first = ensure_active_conversation(settings)
  second = ensure_active_conversation(settings)

  assert isinstance(first, Conversation)
  assert first is second
  assert settings.active_conversation is first


def test_conversation_clear_does_not_allocate():
  settings = SimpleNamespace(active_conversation=Conversation(title="Old"))
  command = ConversationCommand(registry=object(), settings=settings, current_mode="interactive")

  result = command._clear_conversation()

  assert result.is_success()
  assert settings.active_conversation is None
  assert "Cleared conversation: Old" in result.get_data()
  assert "next query" in result.get_data()


def test_conversation_clear_when_none_stays_none():
  settings = SimpleNamespace(active_conversation=None)
  command = ConversationCommand(registry=object(), settings=settings, current_mode="interactive")

  result = command._clear_conversation()

  assert result.is_success()
  assert settings.active_conversation is None
  assert result.get_data() == "No active conversation."
