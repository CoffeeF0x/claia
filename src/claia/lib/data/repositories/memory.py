"""
In-memory repository for media files.

Stores files in memory for testing and temporary usage.
"""

# External dependencies
import logging
from typing import Optional, List, Dict, Any

# Internal dependencies
from .base import FileRepository
from ..models import BaseFile


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                        MEMORY REPOSITORY                             #
########################################################################
class MemoryRepository(FileRepository):
    """
    In-memory implementation of FileRepository.

    Stores files in a dictionary for fast access.
    All data is lost when the process exits.
    """

    def __init__(self):
        """Initialize the memory repository with an empty dictionary."""
        self._files: Dict[str, BaseFile] = {}

    def save(self, file: BaseFile) -> bool:
        """
        Save a file to memory.

        Args:
            file: The file to save

        Returns:
            bool: Always returns True
        """
        try:
            # Store a copy via serialization
            data = file.to_dict()
            
            # Recreate file from dict to avoid reference issues
            file_type = type(file)
            file_copy = file_type.from_dict(data)
            
            # Preserve content if loaded
            if file.has_content_loaded():
                file_copy._content = file._content
                file_copy._content_loaded = True
            
            self._files[file.id] = file_copy
            
            logger.debug(f"Saved file {file.id} to memory")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save file {file.id} to memory: {e}")
            return False

    def load(self, file_id: str, load_content: bool = False) -> Optional[BaseFile]:
        """
        Load a file from memory.

        Args:
            file_id: The ID of the file to load
            load_content: Whether to load content (always available in memory)

        Returns:
            Optional[BaseFile]: The loaded file, or None if not found
        """
        try:
            if file_id not in self._files:
                logger.warning(f"File not found in memory: {file_id}")
                return None
            
            # Return a copy
            stored = self._files[file_id]
            data = stored.to_dict()
            
            file_type = type(stored)
            file_copy = file_type.from_dict(data)
            
            # Copy content if requested and available
            if load_content and stored.has_content_loaded():
                file_copy._content = stored._content
                file_copy._content_loaded = True
            
            logger.debug(f"Loaded file {file_id} from memory")
            return file_copy
        
        except Exception as e:
            logger.error(f"Failed to load file {file_id} from memory: {e}")
            return None

    def delete(self, file_id: str) -> bool:
        """
        Delete a file from memory.

        Args:
            file_id: The ID of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        if file_id in self._files:
            del self._files[file_id]
            logger.info(f"Deleted file {file_id} from memory")
            return True
        else:
            logger.warning(f"File not found for deletion in memory: {file_id}")
            return False

    def exists(self, file_id: str) -> bool:
        """Check if a file exists in memory."""
        return file_id in self._files

    def list_all(self, file_type: Optional[str] = None) -> List[dict]:
        """
        List all files with metadata.

        Args:
            file_type: Optional filter by file type

        Returns:
            List[dict]: List of file metadata
        """
        try:
            files = []
            
            for file in self._files.values():
                metadata = file.to_dict()
                
                # Filter by file type if specified
                if file_type and metadata.get('file_type') != file_type:
                    continue
                
                files.append(metadata)
            
            # Sort by updated_at
            files.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
            
            return files
        
        except Exception as e:
            logger.error(f"Failed to list files from memory: {e}")
            return []

    def clear(self) -> None:
        """
        Clear all files from memory.

        Useful for resetting state between tests.
        """
        self._files.clear()
        logger.debug("Cleared all files from memory")

    def count(self) -> int:
        """
        Get the number of files in memory.

        Returns:
            int: Number of files
        """
        return len(self._files)

