"""
Image file data model.

Handles image files with PIL Image support.
"""

# External dependencies
import logging
import time
from typing import Dict, Any, Optional, Tuple

# Internal dependencies
from .base import BaseFile


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                             IMAGE FILE                               #
########################################################################
class ImageFile(BaseFile):
    """
    Image file model.

    Handles image files with PIL Image support.
    Content is loaded as a PIL Image object.
    """

    def __init__(self,
                 file_name: str,
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 format: Optional[str] = None,
                 **kwargs):
        """
        Initialize an image file.

        Args:
            file_name: Name of the file
            width: Image width in pixels
            height: Image height in pixels
            format: Image format (PNG, JPEG, etc.)
            **kwargs: Additional arguments for BaseFile
        """
        # Set image MIME type if not provided
        if 'mime_type' not in kwargs:
            kwargs['mime_type'] = self._detect_image_mime_type(file_name)
        
        super().__init__(file_name=file_name, **kwargs)
        
        # Image-specific metadata
        self.width = width
        self.height = height
        self.format = format or self._detect_format(file_name)
        
        # Store in metadata as well
        if width:
            self.metadata['width'] = width
        if height:
            self.metadata['height'] = height
        if self.format:
            self.metadata['format'] = self.format

    def _detect_image_mime_type(self, file_name: str) -> str:
        """Detect MIME type for image files."""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
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

    def _detect_format(self, file_name: str) -> str:
        """Detect image format from file name."""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
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
        """
        Load image content as PIL Image.

        This is called by the repository when loading content.
        The repository will set self._content with the PIL Image.

        Returns:
            PIL Image or None if not loaded
        """
        if self._content_loaded and self._content is not None:
            return self._content
        
        # Content should be loaded by repository
        logger.warning(f"Content not loaded for file {self.id}. Use repository.load() with load_content=True")
        return None

    def set_content(self, image_obj) -> None:
        """
        Set the content (used by repository after loading).

        Args:
            image_obj: PIL Image object
        """
        self._content = image_obj
        self._content_loaded = True
        
        # Update dimensions if available
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
        """
        Get content (loads if not already loaded).

        Returns:
            PIL Image object
        """
        return self.load_content()

    @property
    def dimensions(self) -> Optional[Tuple[int, int]]:
        """Get image dimensions (width, height)."""
        if self.width and self.height:
            return (self.width, self.height)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if self.width:
            data['width'] = self.width
        if self.height:
            data['height'] = self.height
        if self.format:
            data['format'] = self.format
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageFile':
        """
        Create image file from dictionary.

        Args:
            data: Dictionary containing file data

        Returns:
            ImageFile: New image file instance
        """
        return cls(
            file_name=data.get('file_name', 'untitled.jpg'),
            file_id=data.get('id'),
            mime_type=data.get('mime_type'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_path=data.get('source_path'),
            width=data.get('width') or data.get('metadata', {}).get('width'),
            height=data.get('height') or data.get('metadata', {}).get('height'),
            format=data.get('format') or data.get('metadata', {}).get('format'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    @classmethod
    def from_image(cls, image_obj, file_name: str, **kwargs) -> 'ImageFile':
        """
        Create an image file from a PIL Image object.

        Args:
            image_obj: PIL Image object
            file_name: Name for the file
            **kwargs: Additional arguments for BaseFile

        Returns:
            ImageFile: New image file with content set
        """
        # Extract dimensions
        width, height = image_obj.size if hasattr(image_obj, 'size') else (None, None)
        format = image_obj.format if hasattr(image_obj, 'format') else None
        
        file = cls(
            file_name=file_name,
            width=width,
            height=height,
            format=format,
            **kwargs
        )
        
        file._content = image_obj
        file._content_loaded = True
        file.updated_at = time.time()
        
        return file

    @classmethod
    def from_path(cls, source: str, is_reference: bool = False, **kwargs) -> 'ImageFile':
        """
        Create an image file referencing a path.

        Args:
            source: Path to the file
            is_reference: Whether to just reference (True) or import (False)
            **kwargs: Additional arguments

        Returns:
            ImageFile: New image file instance
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
    def from_url(cls, url: str, is_reference: bool = True, **kwargs) -> 'ImageFile':
        """
        Create an image file referencing a URL.

        Args:
            url: URL to the file
            is_reference: Whether to just reference (True) or download (False)
            **kwargs: Additional arguments

        Returns:
            ImageFile: New image file instance
        """
        file_name = kwargs.pop('file_name', url.split('/')[-1] or 'download.jpg')
        
        return cls(
            file_name=file_name,
            is_reference=is_reference,
            source_path=url,
            **kwargs
        )

    @classmethod
    def from_bytes(cls, 
                   image_data: bytes,
                   file_name: str,
                   format: Optional[str] = None,
                   **kwargs) -> 'ImageFile':
        """
        Create an ImageFile from binary image data.
        
        This is a convenience method that creates an ImageFile and stores the
        content in memory. The file should be saved to a repository for persistence.

        Args:
            image_data: Raw image bytes
            file_name: Name for the file
            format: Image format (e.g., 'PNG', 'JPEG'). Detected if not provided.
            **kwargs: Additional arguments for ImageFile

        Returns:
            ImageFile: New image file with content loaded
        """
        try:
            from PIL import Image
            import io
            
            # Open image from bytes
            img = Image.open(io.BytesIO(image_data))
            
            # Detect format if not provided
            if format is None:
                format = img.format
            
            # Extract dimensions
            width, height = img.size
            
            # Update metadata
            if 'metadata' not in kwargs:
                kwargs['metadata'] = {}
            kwargs['metadata'].update({
                'width': width,
                'height': height,
                'format': format,
                'size_bytes': len(image_data)
            })
            
            # Create the file
            file = cls(
                file_name=file_name,
                width=width,
                height=height,
                format=format,
                size=len(image_data),
                **kwargs
            )
            
            # Store the image content
            file._content = img
            file._content_loaded = True
            file.updated_at = time.time()
            
            return file
            
        except ImportError:
            logger.error("PIL not available, cannot create image from bytes")
            raise
        except Exception as e:
            logger.error(f"Failed to create image from bytes: {e}")
            raise

