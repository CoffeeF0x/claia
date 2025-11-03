"""
Abstract base repository for media file persistence.

Defines the interface that all file repositories must implement.
"""

# External dependencies
from abc import ABC, abstractmethod
from typing import Optional, List
import logging

# Internal dependencies
from ..models import BaseFile


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                          FILE REPOSITORY                             #
########################################################################
class FileRepository(ABC):
    """
    Abstract base class for file persistence.

    This interface defines the contract that all file repositories
    must implement, enabling pluggable storage backends.
    """

    @abstractmethod
    def save(self, file: BaseFile) -> bool:
        """
        Save a file.

        Args:
            file: The file to save

        Returns:
            bool: True if save was successful, False otherwise
        """
        pass

    @abstractmethod
    def load(self, file_id: str, load_content: bool = False) -> Optional[BaseFile]:
        """
        Load a file by ID.

        Args:
            file_id: The ID of the file to load
            load_content: Whether to load the file content (lazy loading)

        Returns:
            Optional[BaseFile]: The loaded file, or None if not found
        """
        pass

    @abstractmethod
    def delete(self, file_id: str) -> bool:
        """
        Delete a file.

        Args:
            file_id: The ID of the file to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    def exists(self, file_id: str) -> bool:
        """
        Check if a file exists.

        Args:
            file_id: The ID of the file to check

        Returns:
            bool: True if the file exists, False otherwise
        """
        pass

    def load_multiple(self, file_ids: List[str], load_content: bool = False) -> List[BaseFile]:
        """
        Load multiple files efficiently.

        Args:
            file_ids: List of file IDs to load
            load_content: Whether to load file contents

        Returns:
            List[BaseFile]: List of loaded files (skips files that don't exist)
        """
        files = []
        for file_id in file_ids:
            file = self.load(file_id, load_content=load_content)
            if file:
                files.append(file)
        return files

    @abstractmethod
    def list_all(self, file_type: Optional[str] = None) -> List[dict]:
        """
        List all files with metadata.

        Args:
            file_type: Optional filter by file type (e.g., 'images', 'texts')

        Returns:
            List[dict]: List of file metadata dictionaries
        """
        pass

    def create_from_path(self, source: str, is_reference: bool = False, **kwargs) -> BaseFile:
        """
        Factory method: Create appropriate file type from path.

        Detects file type and creates the correct model.

        Args:
            source: Path to the file
            is_reference: Whether to reference or import
            **kwargs: Additional arguments for file creation

        Returns:
            BaseFile: Created file instance
        """
        from ..models import TextFile, ImageFile, AudioFile
        import os
        import mimetypes
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(source)
        mime_type = mime_type or "application/octet-stream"
        
        # Get filename
        file_name = kwargs.pop('file_name', os.path.basename(source))
        
        # Create appropriate file type
        if mime_type.startswith('image/'):
            return ImageFile.from_path(source, is_reference=is_reference, file_name=file_name, **kwargs)
        elif mime_type.startswith('audio/'):
            return AudioFile.from_path(source, is_reference=is_reference, file_name=file_name, **kwargs)
        elif mime_type.startswith('text/') or mime_type in ['application/json', 'application/xml']:
            return TextFile.from_path(source, is_reference=is_reference, file_name=file_name, **kwargs)
        else:
            # Default to text file for unknown types
            return TextFile.from_path(source, is_reference=is_reference, file_name=file_name, **kwargs)

    def create_from_url(self, url: str, is_reference: bool = True, **kwargs) -> BaseFile:
        """
        Factory method: Create appropriate file type from URL.

        Args:
            url: URL to the file
            is_reference: Whether to reference or download
            **kwargs: Additional arguments for file creation

        Returns:
            BaseFile: Created file instance
        """
        from ..models import TextFile, ImageFile, AudioFile
        import mimetypes
        
        # Detect MIME type from URL
        mime_type, _ = mimetypes.guess_type(url)
        mime_type = mime_type or "application/octet-stream"
        
        # Get filename
        file_name = kwargs.pop('file_name', url.split('/')[-1] or 'download')
        
        # Create appropriate file type
        if mime_type.startswith('image/'):
            return ImageFile.from_url(url, is_reference=is_reference, file_name=file_name, **kwargs)
        elif mime_type.startswith('audio/'):
            return AudioFile.from_url(url, is_reference=is_reference, file_name=file_name, **kwargs)
        elif mime_type.startswith('text/') or mime_type in ['application/json', 'application/xml']:
            return TextFile.from_url(url, is_reference=is_reference, file_name=file_name, **kwargs)
        else:
            # Default to text file for unknown types
            return TextFile.from_url(url, is_reference=is_reference, file_name=file_name, **kwargs)

    # @classmethod
    # def create_file_system(cls, base_directory: str) -> 'FileRepository':
    #     """
    #     Factory method to create a file system repository.

    #     Args:
    #         base_directory: Base directory for file storage

    #     Returns:
    #         FileRepository: File system repository instance
    #     """
    #     from .file_system import FileSystemRepository
    #     return FileSystemRepository(base_directory)

    # @classmethod
    # def create_memory(cls) -> 'FileRepository':
    #     """
    #     Factory method to create a memory repository.

    #     Returns:
    #         FileRepository: Memory repository instance
    #     """
    #     from .memory import MemoryRepository
    #     return MemoryRepository()
