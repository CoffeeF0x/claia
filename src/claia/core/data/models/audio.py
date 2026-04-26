"""
Audio artifact data model.

Handles audio content with metadata support.
"""

import logging
import base64
import time
from typing import Dict, Any, Optional

from .base import BaseArtifact


logger = logging.getLogger(__name__)


class AudioArtifact(BaseArtifact):
    """
    Audio artifact model.

    Handles audio artifacts with duration and format metadata.
    Content is loaded as bytes.
    """

    def __init__(self,
                 name: str = "untitled.mp3",
                 duration: Optional[float] = None,
                 format: Optional[str] = None,
                 sample_rate: Optional[int] = None,
                 channels: Optional[int] = None,
                 **kwargs):
        if 'media_type' not in kwargs:
            kwargs['media_type'] = self._detect_audio_media_type(name)

        super().__init__(name=name, **kwargs)

        self.duration = duration
        self.format = format or self._detect_format(name)
        self.sample_rate = sample_rate
        self.channels = channels

        if duration:
            self.metadata['duration'] = duration
        if self.format:
            self.metadata['format'] = self.format
        if sample_rate:
            self.metadata['sample_rate'] = sample_rate
        if channels:
            self.metadata['channels'] = channels

    def _detect_audio_media_type(self, name: str) -> str:
        ext = name.lower().split('.')[-1] if '.' in name else ''
        audio_types = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
            'flac': 'audio/flac',
            'aac': 'audio/aac',
            'm4a': 'audio/mp4',
            'wma': 'audio/x-ms-wma',
            'opus': 'audio/opus',
        }
        return audio_types.get(ext, 'audio/mpeg')

    def _detect_format(self, name: str) -> str:
        ext = name.lower().split('.')[-1] if '.' in name else ''
        return ext.upper() if ext else 'MP3'

    def load_content(self) -> bytes:
        if self._content_loaded and self._content is not None:
            return self._content
        logger.warning(f"Content not loaded for artifact {self.id}.")
        return b""

    def set_content(self, audio_data: bytes) -> None:
        self._content = audio_data
        self._content_loaded = True
        self.size = len(audio_data)
        self.updated_at = time.time()

    @property
    def content(self) -> bytes:
        return self.load_content()

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.duration:
            data['duration'] = self.duration
        if self.format:
            data['format'] = self.format
        if self.sample_rate:
            data['sample_rate'] = self.sample_rate
        if self.channels:
            data['channels'] = self.channels
        if self._content_loaded and self._content is not None:
            data['content_encoding'] = 'base64'
            data['content'] = base64.b64encode(self._content).decode('ascii')
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioArtifact':
        artifact = cls(
            name=data.get('name', 'untitled.mp3'),
            id=data.get('id'),
            media_type=data.get('media_type'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_uri=data.get('source_uri'),
            duration=data.get('duration') or data.get('metadata', {}).get('duration'),
            format=data.get('format') or data.get('metadata', {}).get('format'),
            sample_rate=data.get('sample_rate') or data.get('metadata', {}).get('sample_rate'),
            channels=data.get('channels') or data.get('metadata', {}).get('channels'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )
        if data.get('content_encoding') == 'base64' and data.get('content'):
            try:
                artifact._content = base64.b64decode(data['content'])
                artifact._content_loaded = True
            except Exception as e:
                logger.warning(f"Failed to decode audio content for artifact {data.get('id')}: {e}")
        return artifact

    @classmethod
    def from_bytes(cls, audio_data: bytes, name: str, **kwargs) -> 'AudioArtifact':
        artifact = cls(name=name, **kwargs)
        artifact._content = audio_data
        artifact._content_loaded = True
        artifact.size = len(audio_data)
        artifact.updated_at = time.time()
        return artifact

    @classmethod
    def from_path(cls, source: str, is_reference: bool = False, **kwargs) -> 'AudioArtifact':
        import os
        name = kwargs.pop('name', os.path.basename(source))
        return cls(name=name, is_reference=is_reference, source_uri=source, **kwargs)

    @classmethod
    def from_url(cls, url: str, is_reference: bool = True, **kwargs) -> 'AudioArtifact':
        name = kwargs.pop('name', url.split('/')[-1] or 'download.mp3')
        return cls(name=name, is_reference=is_reference, source_uri=url, **kwargs)
