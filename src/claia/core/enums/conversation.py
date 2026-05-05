# External dependencies
from enum import Enum


class MessageRole(Enum):
    """Enum for message roles in a conversation.

    Roles:
      USER       — a turn produced by the human user.
      ASSISTANT  — a turn produced by the model.
      SYSTEM     — instructions injected by the application
                   (system prompt, etc.).
      INTERNAL   — application-generated context that should still
                   be sent back to the model on the next turn.
      UTILITY    — a sibling message derived from an assistant
                   message: a parsed tag span (tool call, thinking,
                   reference) carrying ``tag_type`` /
                   ``source_message_id`` / ``start_index`` /
                   ``end_index`` / ``attributes``. Stored inline in
                   ``Conversation.messages`` but excluded from the
                   default linearization sent to models. See
                   ``tools-overhaul-plan.md`` §2.4 / §4.
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    INTERNAL = "internal"
    UTILITY = "utility"
