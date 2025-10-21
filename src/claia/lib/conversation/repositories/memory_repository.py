"""
In-memory conversation repository.

Stores conversations in memory using a dictionary. Useful for testing
and scenarios where persistence is not needed.
"""

# External dependencies
import logging
from typing import Dict, Any, Optional, List
import copy

# Internal dependencies
from .base import ConversationRepository
from ..models import Conversation


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                      MEMORY CONVERSATION REPOSITORY                  #
########################################################################
class MemoryRepository(ConversationRepository):
    """
    In-memory implementation of ConversationRepository.

    Stores conversations in a dictionary for fast access. All data is
    lost when the process exits. Primarily useful for:
    - Unit tests
    - Temporary conversations
    - Development/debugging

    Thread-safe: Operations are performed on the dictionary directly,
    which is thread-safe for basic operations in Python.
    """

    def __init__(self):
        """Initialize the memory repository with an empty dictionary."""
        self._conversations: Dict[str, Conversation] = {}

    def save(self, conversation: Conversation) -> bool:
        """
        Save a conversation to memory.

        Creates a deep copy of the conversation to prevent external
        modifications from affecting the stored version.

        Args:
            conversation: The conversation to save

        Returns:
            bool: Always returns True (save cannot fail in memory)
        """
        try:
            # Store a deep copy to prevent external modifications
            # We do this by serializing and deserializing
            data = conversation.to_dict()
            conversation_copy = Conversation.from_dict(data)
            self._conversations[conversation.id] = conversation_copy
            
            logger.debug(f"Saved conversation {conversation.id} to memory")
            return True

        except Exception as e:
            logger.error(f"Failed to save conversation {conversation.id} to memory: {e}")
            return False

    def load(self, conversation_id: str) -> Optional[Conversation]:
        """
        Load a conversation from memory.

        Returns a deep copy to prevent external modifications.

        Args:
            conversation_id: The ID of the conversation to load

        Returns:
            Optional[Conversation]: The loaded conversation, or None if not found
        """
        try:
            if conversation_id not in self._conversations:
                logger.warning(f"Conversation not found in memory: {conversation_id}")
                return None

            # Return a copy to prevent external modifications
            stored = self._conversations[conversation_id]
            data = stored.to_dict()
            conversation_copy = Conversation.from_dict(data)
            
            logger.debug(f"Loaded conversation {conversation_id} from memory")
            return conversation_copy

        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id} from memory: {e}")
            return None

    def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation from memory.

        Args:
            conversation_id: The ID of the conversation to delete

        Returns:
            bool: True if deletion was successful, False if not found
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info(f"Deleted conversation {conversation_id} from memory")
            return True
        else:
            logger.warning(f"Cannot delete: conversation not found in memory: {conversation_id}")
            return False

    def list_all(self) -> List[Dict[str, Any]]:
        """
        List all conversations with their metadata.

        Returns:
            List[Dict[str, Any]]: List of conversation metadata dictionaries
        """
        try:
            conversations = []
            
            for conversation in self._conversations.values():
                metadata = {
                    "id": conversation.id,
                    "title": conversation.title,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                    "message_count": len(conversation.messages),
                    "tool_count": len(conversation.tool_definitions)
                }
                conversations.append(metadata)

            # Sort by updated_at (most recent first)
            conversations.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            
            return conversations

        except Exception as e:
            logger.error(f"Failed to list conversations from memory: {e}")
            return []

    def find_by_criteria(self, **filters) -> List[Conversation]:
        """
        Find conversations matching specific criteria.

        Supported filters:
        - title: Partial match on title (case-insensitive)
        - created_after: Unix timestamp
        - created_before: Unix timestamp
        - has_tools: Boolean - whether conversation has tool definitions

        Args:
            **filters: Filter criteria

        Returns:
            List[Conversation]: List of matching conversations
        """
        try:
            matching_conversations = []
            
            for conversation in self._conversations.values():
                matches = True
                
                if "title" in filters:
                    title_filter = filters["title"].lower()
                    conv_title = conversation.title.lower()
                    if title_filter not in conv_title:
                        matches = False
                
                if "created_after" in filters:
                    if conversation.created_at < filters["created_after"]:
                        matches = False
                
                if "created_before" in filters:
                    if conversation.created_at > filters["created_before"]:
                        matches = False
                
                if "has_tools" in filters:
                    has_tools = len(conversation.tool_definitions) > 0
                    if has_tools != filters["has_tools"]:
                        matches = False
                
                if matches:
                    # Return a copy
                    data = conversation.to_dict()
                    conversation_copy = Conversation.from_dict(data)
                    matching_conversations.append(conversation_copy)
            
            return matching_conversations

        except Exception as e:
            logger.error(f"Failed to find conversations by criteria in memory: {e}")
            return []

    def exists(self, conversation_id: str) -> bool:
        """
        Check if a conversation exists in memory.

        Args:
            conversation_id: The ID of the conversation to check

        Returns:
            bool: True if the conversation exists, False otherwise
        """
        return conversation_id in self._conversations

    def clear(self) -> None:
        """
        Clear all conversations from memory.

        Useful for resetting state between tests.
        """
        self._conversations.clear()
        logger.debug("Cleared all conversations from memory")

    def count(self) -> int:
        """
        Get the number of conversations in memory.

        Returns:
            int: Number of conversations
        """
        return len(self._conversations)

