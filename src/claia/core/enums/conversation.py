# External dependencies
from enum import Enum, auto


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


class TagType(Enum):
    """Enum for types of tags that can appear in message content."""
    TOOL_CALL = "[TOOL_CALL]"
    THINKING = "[THINKING]"


class TagStatus(Enum):
    """Enum for the status of a parsed tag."""
    OPEN = auto()               # Tag has been opened but not yet closed (used internally during parsing)
    CLOSED = auto()             # Tag was opened and correctly closed.
    CLOSED_MISMATCH = auto()    # Tag was opened, but closed by a different tag type.
    MALFORMED_UNCLOSED = auto() # Tag was opened but never closed by the end of the content.
    MALFORMED_UNOPENED = auto() # Closing tag found without a corresponding open tag (optional, could just ignore).
