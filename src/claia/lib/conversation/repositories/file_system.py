"""
File-based conversation repository.

Stores conversations as individual JSON files on disk, with no separate manifest needed.
Each conversation is a self-contained file named {conversation_id}.json.
"""

# External dependencies
import os
import json
import logging
from typing import Dict, Any, Optional, List
import tempfile
import shutil

# Internal dependencies
from .base import ConversationRepository
from ..models import Conversation


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                      FILE CONVERSATION REPOSITORY                    #
########################################################################
class FileConversationRepository(ConversationRepository):
    """
    File-based implementation of ConversationRepository.

    Stores each conversation as a single JSON file in a specified directory.
    No manifest or index file is needed - the repository simply scans the
    directory when listing conversations.

    File structure:
        conversations/
          ├── abc-123-def.json  (conversation with id "abc-123-def")
          ├── xyz-456-ghi.json  (conversation with id "xyz-456-ghi")
          └── ...

    Features:
    - Simple: One file per conversation
    - Atomic: Save operations use atomic file writes
    - Transparent: Users can read/edit JSON files directly
    - No sync issues: No separate manifest to keep in sync
    """

    def __init__(self, base_directory: str):
        """
        Initialize the file conversation repository.

        Args:
            base_directory: Base directory for storing conversation files
        """
        self.base_directory = base_directory
        self.conversations_dir = os.path.join(base_directory, "conversations")
        
        # Ensure the conversations directory exists
        os.makedirs(self.conversations_dir, exist_ok=True)

    def _get_file_path(self, conversation_id: str) -> str:
        """
        Get the file path for a conversation.

        Args:
            conversation_id: The ID of the conversation

        Returns:
            str: The full file path
        """
        return os.path.join(self.conversations_dir, f"{conversation_id}.json")

    def save(self, conversation: Conversation) -> bool:
        """
        Save a conversation to a JSON file.

        Uses atomic write (write to temp file, then rename) to prevent
        corruption if the write is interrupted.

        Args:
            conversation: The conversation to save

        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            file_path = self._get_file_path(conversation.id)
            
            # Serialize conversation to JSON
            data = conversation.to_dict()
            json_content = json.dumps(data, indent=2)

            # Atomic write: write to temp file, then rename
            # This prevents partial writes if the operation is interrupted
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.conversations_dir,
                suffix='.tmp',
                prefix=f'{conversation.id}_'
            )
            
            try:
                # Write to temp file
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                
                # Atomic rename (replaces existing file if present)
                shutil.move(temp_path, file_path)
                
                logger.debug(f"Saved conversation {conversation.id} to {file_path}")
                return True
                
            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e

        except Exception as e:
            logger.error(f"Failed to save conversation {conversation.id}: {e}")
            return False

    def load(self, conversation_id: str) -> Optional[Conversation]:
        """
        Load a conversation from a JSON file.

        Args:
            conversation_id: The ID of the conversation to load

        Returns:
            Optional[Conversation]: The loaded conversation, or None if not found
        """
        try:
            file_path = self._get_file_path(conversation_id)
            
            if not os.path.exists(file_path):
                logger.warning(f"Conversation file not found: {file_path}")
                return None

            # Load and parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Create conversation from dictionary
            conversation = Conversation.from_dict(data)
            
            logger.debug(f"Loaded conversation {conversation_id} from {file_path}")
            return conversation

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse conversation JSON {conversation_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id}: {e}")
            return None

    def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation file.

        Args:
            conversation_id: The ID of the conversation to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            file_path = self._get_file_path(conversation_id)
            
            if not os.path.exists(file_path):
                logger.warning(f"Cannot delete: conversation file not found: {file_path}")
                return False

            os.remove(file_path)
            logger.info(f"Deleted conversation {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False

    def list_all(self) -> List[Dict[str, Any]]:
        """
        List all conversations with their metadata.

        Scans the conversations directory and returns metadata for each file.

        Returns:
            List[Dict[str, Any]]: List of conversation metadata dictionaries
        """
        try:
            conversations = []
            
            # Scan directory for JSON files
            if not os.path.exists(self.conversations_dir):
                return conversations

            for filename in os.listdir(self.conversations_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(self.conversations_dir, filename)
                
                try:
                    # Load minimal metadata from file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract metadata (don't load full messages/actions for performance)
                    metadata = {
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "message_count": len(data.get("messages", [])),
                        "tool_count": len(data.get("tool_definitions", []))
                    }
                    conversations.append(metadata)
                    
                except Exception as e:
                    logger.warning(f"Failed to read metadata from {filename}: {e}")
                    continue

            # Sort by updated_at (most recent first)
            conversations.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            
            return conversations

        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
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
            
            # Get all conversation metadata
            all_metadata = self.list_all()
            
            for metadata in all_metadata:
                # Apply filters
                matches = True
                
                if "title" in filters:
                    title_filter = filters["title"].lower()
                    conv_title = metadata.get("title", "").lower()
                    if title_filter not in conv_title:
                        matches = False
                
                if "created_after" in filters:
                    if metadata.get("created_at", 0) < filters["created_after"]:
                        matches = False
                
                if "created_before" in filters:
                    if metadata.get("created_at", float('inf')) > filters["created_before"]:
                        matches = False
                
                if "has_tools" in filters:
                    has_tools = metadata.get("tool_count", 0) > 0
                    if has_tools != filters["has_tools"]:
                        matches = False
                
                # Load full conversation if it matches
                if matches:
                    conversation = self.load(metadata["id"])
                    if conversation:
                        matching_conversations.append(conversation)
            
            return matching_conversations

        except Exception as e:
            logger.error(f"Failed to find conversations by criteria: {e}")
            return []

    def exists(self, conversation_id: str) -> bool:
        """
        Check if a conversation exists.

        Args:
            conversation_id: The ID of the conversation to check

        Returns:
            bool: True if the conversation exists, False otherwise
        """
        file_path = self._get_file_path(conversation_id)
        return os.path.exists(file_path)

