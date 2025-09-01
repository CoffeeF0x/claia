# External dependencies
from enum import Enum, auto


########################################################################
#                                ENUMS                                 #
########################################################################
class ActionType(Enum):
    """Enum for types of actions that can occur in a conversation."""
    CREATE_CONVERSATION    = auto()
    CHANGE_PROMPT          = auto()
    CHANGE_SYSTEM_PROMPT   = auto()
    CHANGE_TOOL_PROMPT     = auto()
    CREATE_MESSAGE         = auto()
    UPDATE_MESSAGE         = auto()
    DELETE_MESSAGE         = auto()
    ATTACH_FILE            = auto()
    DETACH_FILE            = auto()
    PROCESS_MESSAGE        = auto()
    CHANGE_TITLE           = auto()
    ADD_TOOL_DEFINITION    = auto()
    UPDATE_TOOL_DEFINITION = auto()
    REMOVE_TOOL_DEFINITION = auto()
    PROCESS_FUNCTION_CALL  = auto()
    START_STREAM           = auto()
    END_STREAM             = auto()
    UPDATE_SETTINGS        = auto()
    REPLACE_TOOL_CALL      = auto()
    FAILED_TOOL_CALL       = auto()


class MessageRole(Enum):
    """Enum for message roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    INTERNAL = "internal"


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
