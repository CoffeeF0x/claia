"""
Base file data model.

Pure data model for files without persistence logic.
All file types inherit from this base class.
"""

# External dependencies
import uuid
import time
import mimetypes
import logging
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod

# Internal dependencies
from ...enums.file import FileSubdirectory


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                              BASE FILE                               #
########################################################################
class BaseFile(ABC):
    """
    Base class for all file models.

    This is a pure data model that represents file metadata.
    Content is lazily loaded on demand via load_content().

    Attributes:
        id: Unique identifier for the file
        file_name: Name of the file
        mime_type: MIME type of the file
        size: Size in bytes (0 if not yet loaded)
        is_reference: Whether this file references an external source
        source_path: Original path/URL if this is a reference
        metadata: Additional metadata dictionary
        created_at: Creation timestamp
        updated_at: Last update timestamp
        _content: Cached content (None until loaded)
    """

    def __init__(self,
                 file_name: str,
                 mime_type: Optional[str] = None,
                 file_id: Optional[str] = None,
                 size: int = 0,
                 is_reference: bool = False,
                 source_path: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None):
        """
        Initialize a file model.

        Args:
            file_name: Name of the file
            mime_type: MIME type (auto-detected if not provided)
            file_id: Optional ID (generated if not provided)
            size: Size in bytes
            is_reference: Whether this references an external file
            source_path: Original path/URL for references
            metadata: Additional metadata
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        self.id = file_id or str(uuid.uuid4())
        self.file_name = file_name
        self.mime_type = mime_type or self._detect_mime_type(file_name)
        self.size = size
        self.is_reference = is_reference
        self.source_path = source_path
        self.metadata = metadata or {}
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at
        
        # Content cache (lazy loaded)
        self._content: Optional[Union[str, bytes]] = None
        self._content_loaded = False

    def _detect_mime_type(self, file_name: str) -> str:
        """
        Detect MIME type from file name.

        Args:
            file_name: Name of the file

        Returns:
            str: Detected MIME type or application/octet-stream
        """
        detected = mimetypes.guess_type(file_name)[0]
        return detected or "application/octet-stream"

    def get_file_type(self) -> FileSubdirectory:
        """Get the file type enum based on MIME type."""
        return FileSubdirectory.from_mime_type(self.mime_type)

    @abstractmethod
    def load_content(self) -> Union[str, bytes, Any]:
        """
        Load the file content.

        This is implemented by subclasses to load content in the
        appropriate format (text string, bytes, PIL Image, etc.)

        Returns:
            The loaded content in the appropriate format
        """
        pass

    def has_content_loaded(self) -> bool:
        """Check if content has been loaded."""
        return self._content_loaded

    def clear_content_cache(self) -> None:
        """Clear the cached content to free memory."""
        self._content = None
        self._content_loaded = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert file to dictionary.

        Note: Does not include content - that's loaded separately.

        Returns:
            Dict with file metadata
        """
        return {
            "id": self.id,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "size": self.size,
            "is_reference": self.is_reference,
            "source_path": self.source_path,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "file_type": self.get_file_type().value
        }

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseFile':
        """
        Create file from dictionary.

        Implemented by subclasses to handle their specific fields.

        Args:
            data: Dictionary containing file data

        Returns:
            File instance
        """
        pass

    @staticmethod
    def is_url(source: str) -> bool:
        """
        Check if a source string is a URL.

        Args:
            source: Source string to check

        Returns:
            bool: True if the source appears to be a URL
        """
        return source.startswith(('http://', 'https://', 'ftp://'))

    def __repr__(self) -> str:
        """String representation of the file."""
        ref_indicator = " (ref)" if self.is_reference else ""
        return f"<{self.__class__.__name__} id={self.id[:8]}... name={self.file_name}{ref_indicator}>"

