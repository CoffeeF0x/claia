"""
Abstract base repository for conversation persistence.

Defines the interface that all conversation repositories must implement,
allowing for pluggable storage backends (files, databases, memory, etc.).
"""

# External dependencies
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

# Internal dependencies
from ..models import Conversation


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                        CONVERSATION REPOSITORY                       #
########################################################################
class ConversationRepository(ABC):
    """
    Abstract base class for conversation persistence.

    This interface defines the contract that all conversation repositories
    must implement, enabling pluggable storage backends while keeping the
    domain models clean and independent of persistence concerns.

    Implementations might include:
    - FileConversationRepository: JSON files on disk
    - DatabaseConversationRepository: SQL or NoSQL databases
    - MemoryRepository: In-memory storage for testing
    """

    @abstractmethod
    def save(self, conversation: Conversation) -> bool:
        """
        Save a conversation.

        Args:
            conversation: The conversation to save

        Returns:
            bool: True if save was successful, False otherwise
        """
        pass

    @abstractmethod
    def load(self, conversation_id: str) -> Optional[Conversation]:
        """
        Load a conversation by ID.

        Args:
            conversation_id: The ID of the conversation to load

        Returns:
            Optional[Conversation]: The loaded conversation, or None if not found
        """
        pass

    @abstractmethod
    def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: The ID of the conversation to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        """
        List all conversations with their metadata.

        Returns:
            List[Dict[str, Any]]: List of conversation metadata dictionaries
        """
        pass

    @abstractmethod
    def find_by_criteria(self, **filters) -> List[Conversation]:
        """
        Find conversations matching specific criteria.

        Args:
            **filters: Filter criteria (implementation-specific)

        Returns:
            List[Conversation]: List of matching conversations
        """
        pass

    @abstractmethod
    def exists(self, conversation_id: str) -> bool:
        """
        Check if a conversation exists.

        Args:
            conversation_id: The ID of the conversation to check

        Returns:
            bool: True if the conversation exists, False otherwise
        """
        pass

