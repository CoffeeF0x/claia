# External dependencies
from enum import Enum, auto


########################################################################
#                                ENUMS                                 #
########################################################################

class ActionType(Enum):
    """Enum for types of actions that can occur in a conversation."""
    CREATE_CONVERSATION = auto()
    CHANGE_PROMPT = auto()
    CREATE_MESSAGE = auto()
    UPDATE_MESSAGE = auto()
    DELETE_MESSAGE = auto()
    ATTACH_FILE = auto()
    DETACH_FILE = auto()
    PROCESS_MESSAGE = auto()
    CHANGE_TITLE = auto()
    ADD_TOOL_DEFINITION = auto()
    UPDATE_TOOL_DEFINITION = auto()
    REMOVE_TOOL_DEFINITION = auto()


class MessageRole(Enum):
    """Enum for message roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TagType(Enum):
    """Enum for types of tags that can appear in message content."""
    TOOL_CALL = "[FUNCTION_CALL]"
    THINKING = "[THINKING]"
