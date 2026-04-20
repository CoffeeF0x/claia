"""
Text artifact data model.

Handles text content with encoding support.
"""

import logging
import time
from typing import Dict, Any, Optional

from .base import BaseArtifact


logger = logging.getLogger(__name__)


class TextArtifact(BaseArtifact):
    """
    Text artifact model.

    Handles text artifacts with encoding support.
    Content is loaded as a string.
    """

    def __init__(self,
                 name: str = "untitled.txt",
                 encoding: str = "utf-8",
                 **kwargs):
        if 'media_type' not in kwargs:
            kwargs['media_type'] = self._detect_text_media_type(name)

        super().__init__(name=name, **kwargs)
        self.encoding = encoding
        self.metadata['encoding'] = encoding

    def _detect_text_media_type(self, name: str) -> str:
        ext = name.lower().split('.')[-1] if '.' in name else ''
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
        if self._content_loaded and self._content is not None:
            return self._content
        logger.warning(f"Content not loaded for artifact {self.id}.")
        return ""

    def set_content(self, content: str) -> None:
        self._content = content
        self._content_loaded = True
        self.size = len(content.encode(self.encoding))
        self.updated_at = time.time()

    @property
    def content(self) -> str:
        return self.load_content()

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['encoding'] = self.encoding
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextArtifact':
        return cls(
            name=data.get('name', 'untitled.txt'),
            id=data.get('id'),
            media_type=data.get('media_type'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_uri=data.get('source_uri'),
            encoding=data.get('encoding', 'utf-8'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    @classmethod
    def from_content(cls, content: str, name: str, encoding: str = "utf-8", **kwargs) -> 'TextArtifact':
        artifact = cls(name=name, encoding=encoding, **kwargs)
        artifact._content = content
        artifact._content_loaded = True
        artifact.size = len(content.encode(encoding))
        artifact.updated_at = time.time()
        return artifact

    @classmethod
    def from_path(cls, source: str, is_reference: bool = False, **kwargs) -> 'TextArtifact':
        import os
        name = kwargs.pop('name', os.path.basename(source))
        return cls(name=name, is_reference=is_reference, source_uri=source, **kwargs)

    @classmethod
    def from_url(cls, url: str, is_reference: bool = True, **kwargs) -> 'TextArtifact':
        name = kwargs.pop('name', url.split('/')[-1] or 'download.txt')
        return cls(name=name, is_reference=is_reference, source_uri=url, **kwargs)
