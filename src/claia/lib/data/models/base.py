"""
Base artifact data model.

Pure data model for domain artifacts without persistence logic.
All artifact types inherit from this base class.
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
class BaseArtifact(ABC):
    """
    Base class for all artifact models.

    This is a pure data model that represents file metadata.
    Content is lazily loaded on demand via load_content().

    Attributes:
        id: Unique identifier for the artifact
        name: Name of the artifact
        media_type: Media type of the artifact
        size: Size in bytes (0 if not yet loaded)
        is_reference: Whether this file references an external source
        source_path: Original path/URL if this is a reference
        metadata: Additional metadata dictionary
        created_at: Creation timestamp
        updated_at: Last update timestamp
        _content: Cached content (None until loaded)
    """

    def __init__(self,
                 file_name: Optional[str] = None,
                 mime_type: Optional[str] = None,
                 file_id: Optional[str] = None,
                 size: int = 0,
                 is_reference: bool = False,
                 source_path: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None,
                 name: Optional[str] = None,
                 media_type: Optional[str] = None,
                 artifact_id: Optional[str] = None,
                 source_uri: Optional[str] = None):
        """
        Initialize a file model.

        Args:
            file_name: Name alias for artifact
            mime_type: Media type alias (auto-detected if not provided)
            file_id: ID alias (generated if not provided)
            size: Size in bytes
            is_reference: Whether this references an external file
            source_path: Original path/URL for references
            metadata: Additional metadata
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        resolved_id = artifact_id or file_id
        resolved_name = name or file_name or "untitled"
        resolved_media_type = media_type or mime_type
        resolved_source_uri = source_uri if source_uri is not None else source_path

        self.id = resolved_id or str(uuid.uuid4())
        self.name = resolved_name
        self.media_type = resolved_media_type or self._detect_mime_type(resolved_name)
        self.size = size
        self.is_reference = is_reference
        self.source_uri = resolved_source_uri
        self.metadata = metadata or {}
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at
        
        # Content cache (lazy loaded)
        self._content: Optional[Union[str, bytes]] = None
        self._content_loaded = False

    def _detect_mime_type(self, artifact_name: str) -> str:
        """
        Detect MIME type from file name.

        Args:
            artifact_name: Name of the artifact

        Returns:
            str: Detected MIME type or application/octet-stream
        """
        detected = mimetypes.guess_type(artifact_name)[0]
        return detected or "application/octet-stream"

    def get_file_type(self) -> FileSubdirectory:
        """Get the file type enum based on media type."""
        return FileSubdirectory.from_mime_type(self.media_type)

    def get_artifact_type(self) -> FileSubdirectory:
        """Alias for get_file_type with domain-focused naming."""
        return self.get_file_type()

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
        data = {
            "id": self.id,
            "name": self.name,
            "media_type": self.media_type,
            "size": self.size,
            "is_reference": self.is_reference,
            "source_uri": self.source_uri,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "file_type": self.get_file_type().value
        }
        return data

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseArtifact':
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
        return f"<{self.__class__.__name__} id={self.id[:8]}... name={self.name}{ref_indicator}>"

    @property
    def file_name(self) -> str:
        return self.name

    @property
    def mime_type(self) -> str:
        return self.media_type

    @property
    def source_path(self) -> Optional[str]:
        return self.source_uri

