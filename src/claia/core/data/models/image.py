"""
Image artifact data model.

Handles image content with PIL Image support.
"""

import base64
import io
import logging
import time
from typing import Dict, Any, Optional, Tuple

from .base import BaseArtifact


logger = logging.getLogger(__name__)


class ImageArtifact(BaseArtifact):
    """
    Image artifact model.

    Handles image artifacts with PIL Image support.
    Content is loaded as a PIL Image object.
    """

    def __init__(self,
                 name: str = "untitled.jpg",
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 format: Optional[str] = None,
                 content_bytes: Optional[bytes] = None,
                 **kwargs):
        if 'media_type' not in kwargs:
            kwargs['media_type'] = self._detect_image_media_type(name)

        super().__init__(name=name, **kwargs)

        self.width = width
        self.height = height
        self.format = format or self._detect_format(name)
        self._content_bytes = content_bytes

        if width:
            self.metadata['width'] = width
        if height:
            self.metadata['height'] = height
        if self.format:
            self.metadata['format'] = self.format

    def _detect_image_media_type(self, name: str) -> str:
        ext = name.lower().split('.')[-1] if '.' in name else ''
        image_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'webp': 'image/webp',
            'svg': 'image/svg+xml',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
            'ico': 'image/x-icon',
        }
        return image_types.get(ext, 'image/jpeg')

    def _detect_format(self, name: str) -> str:
        ext = name.lower().split('.')[-1] if '.' in name else ''
        format_map = {
            'jpg': 'JPEG',
            'jpeg': 'JPEG',
            'png': 'PNG',
            'gif': 'GIF',
            'bmp': 'BMP',
            'webp': 'WEBP',
            'tiff': 'TIFF',
            'tif': 'TIFF',
        }
        return format_map.get(ext, 'JPEG')

    def load_content(self):
        if self._content_loaded and self._content is not None:
            return self._content
        if self._content_bytes:
            try:
                from PIL import Image
                self._content = Image.open(io.BytesIO(self._content_bytes))
                self._content_loaded = True
                return self._content
            except ImportError:
                logger.warning("PIL not available, cannot load image object")
                return None
            except Exception as e:
                logger.warning(f"Could not load image object for artifact {self.id}: {e}")
                return None
        logger.warning(f"Content not loaded for artifact {self.id}.")
        return None

    def load_bytes(self) -> Optional[bytes]:
        """Return the raw image bytes if available."""
        if self._content_bytes:
            return self._content_bytes
        if self._content_loaded and self._content is not None:
            buffer = io.BytesIO()
            self._content.save(buffer, format=self.format or self._detect_format(self.name))
            self._content_bytes = buffer.getvalue()
            self.size = len(self._content_bytes)
            self.metadata['size_bytes'] = self.size
            return self._content_bytes
        return None

    def set_content(self, image_obj) -> None:
        self._content = image_obj
        self._content_loaded = True
        self._content_bytes = None
        if hasattr(image_obj, 'size'):
            self.width, self.height = image_obj.size
            self.metadata['width'] = self.width
            self.metadata['height'] = self.height
        if hasattr(image_obj, 'format'):
            self.format = image_obj.format
            self.metadata['format'] = self.format
        self.updated_at = time.time()

    @property
    def content(self):
        return self.load_content()

    @property
    def dimensions(self) -> Optional[Tuple[int, int]]:
        if self.width and self.height:
            return (self.width, self.height)
        return None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.width:
            data['width'] = self.width
        if self.height:
            data['height'] = self.height
        if self.format:
            data['format'] = self.format
        content_bytes = self.load_bytes()
        if content_bytes:
            data['content_encoding'] = 'base64'
            data['content'] = base64.b64encode(content_bytes).decode('ascii')
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageArtifact':
        content_bytes = None
        if data.get('content_encoding') == 'base64' and data.get('content'):
            try:
                content_bytes = base64.b64decode(data['content'])
            except Exception as e:
                logger.warning(f"Failed to decode image content for artifact {data.get('id')}: {e}")

        return cls(
            name=data.get('name', 'untitled.jpg'),
            id=data.get('id'),
            media_type=data.get('media_type'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_uri=data.get('source_uri'),
            width=data.get('width') or data.get('metadata', {}).get('width'),
            height=data.get('height') or data.get('metadata', {}).get('height'),
            format=data.get('format') or data.get('metadata', {}).get('format'),
            content_bytes=content_bytes,
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    @classmethod
    def from_image(cls, image_obj, name: str, **kwargs) -> 'ImageArtifact':
        width, height = image_obj.size if hasattr(image_obj, 'size') else (None, None)
        fmt = image_obj.format if hasattr(image_obj, 'format') else None
        artifact = cls(name=name, width=width, height=height, format=fmt, **kwargs)
        artifact._content = image_obj
        artifact._content_loaded = True
        artifact.updated_at = time.time()
        return artifact

    @classmethod
    def from_path(cls, source: str, is_reference: bool = False, **kwargs) -> 'ImageArtifact':
        import os
        name = kwargs.pop('name', os.path.basename(source))
        return cls(name=name, is_reference=is_reference, source_uri=source, **kwargs)

    @classmethod
    def from_url(cls, url: str, is_reference: bool = True, **kwargs) -> 'ImageArtifact':
        name = kwargs.pop('name', url.split('/')[-1] or 'download.jpg')
        return cls(name=name, is_reference=is_reference, source_uri=url, **kwargs)

    @classmethod
    def from_bytes(cls,
                   image_data: bytes,
                   name: str,
                   format: Optional[str] = None,
                   **kwargs) -> 'ImageArtifact':
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            if format is None:
                format = img.format
            width, height = img.size

            if 'metadata' not in kwargs:
                kwargs['metadata'] = {}
            kwargs['metadata'].update({
                'width': width,
                'height': height,
                'format': format,
                'size_bytes': len(image_data)
            })

            artifact = cls(
                name=name,
                width=width,
                height=height,
                format=format,
                size=len(image_data),
                content_bytes=image_data,
                **kwargs
            )
            artifact._content = img
            artifact._content_loaded = True
            artifact.updated_at = time.time()
            return artifact

        except ImportError:
            logger.warning("PIL not available, storing image bytes without dimensions")
            if 'metadata' not in kwargs:
                kwargs['metadata'] = {}
            kwargs['metadata'].update({
                'format': format,
                'size_bytes': len(image_data)
            })
            return cls(
                name=name,
                format=format,
                size=len(image_data),
                content_bytes=image_data,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create image from bytes: {e}")
            raise
