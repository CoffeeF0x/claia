"""
Audio file data model.

Handles audio files with metadata support.
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
#                             AUDIO FILE                               #
########################################################################
class AudioFile(BaseFile):
    """
    Audio file model.

    Handles audio files with duration and format metadata.
    Content is loaded as bytes.
    """

    def __init__(self,
                 file_name: str,
                 duration: Optional[float] = None,
                 format: Optional[str] = None,
                 sample_rate: Optional[int] = None,
                 channels: Optional[int] = None,
                 **kwargs):
        """
        Initialize an audio file.

        Args:
            file_name: Name of the file
            duration: Duration in seconds
            format: Audio format (MP3, WAV, etc.)
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            **kwargs: Additional arguments for BaseFile
        """
        # Set audio MIME type if not provided
        if 'mime_type' not in kwargs:
            kwargs['mime_type'] = self._detect_audio_mime_type(file_name)
        
        super().__init__(file_name=file_name, **kwargs)
        
        # Audio-specific metadata
        self.duration = duration
        self.format = format or self._detect_format(file_name)
        self.sample_rate = sample_rate
        self.channels = channels
        
        # Store in metadata as well
        if duration:
            self.metadata['duration'] = duration
        if self.format:
            self.metadata['format'] = self.format
        if sample_rate:
            self.metadata['sample_rate'] = sample_rate
        if channels:
            self.metadata['channels'] = channels

    def _detect_audio_mime_type(self, file_name: str) -> str:
        """Detect MIME type for audio files."""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
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

    def _detect_format(self, file_name: str) -> str:
        """Detect audio format from file name."""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        return ext.upper() if ext else 'MP3'

    def load_content(self) -> bytes:
        """
        Load audio content as bytes.

        This is called by the repository when loading content.
        The repository will set self._content with the audio data.

        Returns:
            bytes: The audio data
        """
        if self._content_loaded and self._content is not None:
            return self._content
        
        # Content should be loaded by repository
        logger.warning(f"Content not loaded for file {self.id}. Use repository.load() with load_content=True")
        return b""

    def set_content(self, audio_data: bytes) -> None:
        """
        Set the content (used by repository after loading).

        Args:
            audio_data: The audio data as bytes
        """
        self._content = audio_data
        self._content_loaded = True
        self.size = len(audio_data)
        self.updated_at = time.time()

    @property
    def content(self) -> bytes:
        """
        Get content (loads if not already loaded).

        Returns:
            bytes: The audio data
        """
        return self.load_content()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if self.duration:
            data['duration'] = self.duration
        if self.format:
            data['format'] = self.format
        if self.sample_rate:
            data['sample_rate'] = self.sample_rate
        if self.channels:
            data['channels'] = self.channels
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioFile':
        """
        Create audio file from dictionary.

        Args:
            data: Dictionary containing file data

        Returns:
            AudioFile: New audio file instance
        """
        return cls(
            file_name=data.get('file_name', 'untitled.mp3'),
            file_id=data.get('id'),
            mime_type=data.get('mime_type'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_path=data.get('source_path'),
            duration=data.get('duration') or data.get('metadata', {}).get('duration'),
            format=data.get('format') or data.get('metadata', {}).get('format'),
            sample_rate=data.get('sample_rate') or data.get('metadata', {}).get('sample_rate'),
            channels=data.get('channels') or data.get('metadata', {}).get('channels'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    @classmethod
    def from_bytes(cls, audio_data: bytes, file_name: str, **kwargs) -> 'AudioFile':
        """
        Create an audio file from bytes.

        Args:
            audio_data: The audio data as bytes
            file_name: Name for the file
            **kwargs: Additional arguments for BaseFile

        Returns:
            AudioFile: New audio file with content set
        """
        file = cls(file_name=file_name, **kwargs)
        file._content = audio_data
        file._content_loaded = True
        file.size = len(audio_data)
        file.updated_at = time.time()
        
        return file

    @classmethod
    def from_path(cls, source: str, is_reference: bool = False, **kwargs) -> 'AudioFile':
        """
        Create an audio file referencing a path.

        Args:
            source: Path to the file
            is_reference: Whether to just reference (True) or import (False)
            **kwargs: Additional arguments

        Returns:
            AudioFile: New audio file instance
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
    def from_url(cls, url: str, is_reference: bool = True, **kwargs) -> 'AudioFile':
        """
        Create an audio file referencing a URL.

        Args:
            url: URL to the file
            is_reference: Whether to just reference (True) or download (False)
            **kwargs: Additional arguments

        Returns:
            AudioFile: New audio file instance
        """
        file_name = kwargs.pop('file_name', url.split('/')[-1] or 'download.mp3')
        
        return cls(
            file_name=file_name,
            is_reference=is_reference,
            source_path=url,
            **kwargs
        )

