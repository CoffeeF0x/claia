"""
Text file data model.

Handles text files with encoding support.
"""

# External dependencies
import logging
import time
from typing import Dict, Any, Optional

# Internal dependencies
from .base import BaseFile


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                              TEXT FILE                               #
########################################################################
class TextFile(BaseFile):
    """
    Text file model.

    Handles text files with encoding support.
    Content is loaded as a string.
    """

    def __init__(self,
                 file_name: str,
                 encoding: str = "utf-8",
                 **kwargs):
        """
        Initialize a text file.

        Args:
            file_name: Name of the file
            encoding: Text encoding (default: utf-8)
            **kwargs: Additional arguments for BaseFile
        """
        # Set text MIME type if not provided
        if 'mime_type' not in kwargs:
            kwargs['mime_type'] = self._detect_text_mime_type(file_name)
        
        super().__init__(file_name=file_name, **kwargs)
        
        self.encoding = encoding
        self.metadata['encoding'] = encoding

    def _detect_text_mime_type(self, file_name: str) -> str:
        """Detect MIME type for text files."""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        text_types = {
            'txt': 'text/plain',
            'md': 'text/markdown',
            'html': 'text/html',
            'htm': 'text/html',
            'css': 'text/css',
            'js': 'text/javascript',
            'json': 'application/json',
            'xml': 'application/xml',
            'csv': 'text/csv',
            'py': 'text/x-python',
            'java': 'text/x-java',
            'c': 'text/x-c',
            'cpp': 'text/x-c++',
            'h': 'text/x-c',
        }
        
        return text_types.get(ext, 'text/plain')

    def load_content(self) -> str:
        """
        Load text content.

        This is called by the repository when loading content.
        The repository will set self._content with the loaded data.

        Returns:
            str: The text content
        """
        if self._content_loaded and self._content is not None:
            return self._content
        
        # Content should be loaded by repository
        logger.warning(f"Content not loaded for file {self.id}. Use repository.load() with load_content=True")
        return ""

    def set_content(self, content: str) -> None:
        """
        Set the content (used by repository after loading).

        Args:
            content: The text content
        """
        self._content = content
        self._content_loaded = True
        self.size = len(content.encode(self.encoding))
        self.updated_at = time.time() if hasattr(self, 'updated_at') else None

    @property
    def content(self) -> str:
        """
        Get content (loads if not already loaded).

        Returns:
            str: The text content
        """
        return self.load_content()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data['encoding'] = self.encoding
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextFile':
        """
        Create text file from dictionary.

        Args:
            data: Dictionary containing file data

        Returns:
            TextFile: New text file instance
        """
        return cls(
            file_name=data.get('file_name', 'untitled.txt'),
            file_id=data.get('id'),
            mime_type=data.get('mime_type'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_path=data.get('source_path'),
            encoding=data.get('encoding', 'utf-8'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    @classmethod
    def from_content(cls, content: str, file_name: str, encoding: str = "utf-8", **kwargs) -> 'TextFile':
        """
        Create a text file from content.

        Args:
            content: The text content
            file_name: Name for the file
            encoding: Text encoding
            **kwargs: Additional arguments for BaseFile

        Returns:
            TextFile: New text file with content set
        """
        import time
        
        file = cls(file_name=file_name, encoding=encoding, **kwargs)
        file._content = content
        file._content_loaded = True
        file.size = len(content.encode(encoding))
        file.updated_at = time.time()
        
        return file

    @classmethod
    def from_path(cls, source: str, is_reference: bool = False, **kwargs) -> 'TextFile':
        """
        Create a text file referencing a path.

        Args:
            source: Path to the file
            is_reference: Whether to just reference (True) or import (False)
            **kwargs: Additional arguments

        Returns:
            TextFile: New text file instance
        """
        import os
        
        file_name = kwargs.pop('file_name', os.path.basename(source))
        
        return cls(
            file_name=file_name,
            is_reference=is_reference,
            source_path=source,
            **kwargs
        )

    @classmethod
    def from_url(cls, url: str, is_reference: bool = True, **kwargs) -> 'TextFile':
        """
        Create a text file referencing a URL.

        Args:
            url: URL to the file
            is_reference: Whether to just reference (True) or download (False)
            **kwargs: Additional arguments

        Returns:
            TextFile: New text file instance
        """
        file_name = kwargs.pop('file_name', url.split('/')[-1] or 'download.txt')
        
        return cls(
            file_name=file_name,
            is_reference=is_reference,
            source_path=url,
            **kwargs
        )

