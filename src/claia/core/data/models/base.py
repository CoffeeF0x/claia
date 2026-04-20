"""
Base artifact data model.

Pure data model for domain artifacts without persistence logic.
All artifact types inherit from this base class.
"""

import uuid
import time
import mimetypes
import logging
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class BaseArtifact(ABC):
    """
    Base class for all artifact models.

    This is a pure data model that represents artifact metadata.
    Content is lazily loaded on demand via load_content().

    Attributes:
        id: Unique identifier for the artifact
        name: Name of the artifact
        media_type: Media type of the artifact (e.g. "text/plain")
        size: Size in bytes (0 if not yet loaded)
        is_reference: Whether this artifact references an external source
        source_uri: Original path/URL if this is a reference
        metadata: Additional metadata dictionary
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    def __init__(self,
                 name: str = "untitled",
                 media_type: Optional[str] = None,
                 id: Optional[str] = None,
                 size: int = 0,
                 is_reference: bool = False,
                 source_uri: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.media_type = media_type or self._detect_media_type(name)
        self.size = size
        self.is_reference = is_reference
        self.source_uri = source_uri
        self.metadata = metadata or {}
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at

        self._content: Optional[Union[str, bytes]] = None
        self._content_loaded = False

    def _detect_media_type(self, name: str) -> str:
        detected = mimetypes.guess_type(name)[0]
        return detected or "application/octet-stream"

    @abstractmethod
    def load_content(self) -> Union[str, bytes, Any]:
        """Load the artifact content. Implemented by subclasses."""
        pass

    def has_content_loaded(self) -> bool:
        return self._content_loaded

    def clear_content_cache(self) -> None:
        self._content = None
        self._content_loaded = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact metadata to dictionary (excludes content)."""
        return {
            "id": self.id,
            "name": self.name,
            "media_type": self.media_type,
            "size": self.size,
            "is_reference": self.is_reference,
            "source_uri": self.source_uri,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseArtifact':
        """Create artifact from dictionary. Implemented by subclasses."""
        pass

    @staticmethod
    def is_url(source: str) -> bool:
        return source.startswith(('http://', 'https://', 'ftp://'))

    def __repr__(self) -> str:
        ref_indicator = " (ref)" if self.is_reference else ""
        return f"<{self.__class__.__name__} id={self.id[:8]}... name={self.name}{ref_indicator}>"
