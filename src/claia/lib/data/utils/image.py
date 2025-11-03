"""
Image utilities for processing image files.

Provides functions for:
- Base64 encoding/decoding
- Format conversion
- Resizing
- Metadata extraction
"""

import base64
import io
import logging
import os
import tempfile
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def to_base64(image_bytes: bytes) -> str:
    """
    Convert image bytes to base64 string.
    
    Args:
        image_bytes: Raw image data
        
    Returns:
        str: Base64-encoded string
    """
    return base64.b64encode(image_bytes).decode('utf-8')


def from_base64(base64_string: str) -> bytes:
    """
    Convert base64 string to image bytes.
    
    Args:
        base64_string: Base64-encoded image data
        
    Returns:
        bytes: Raw image data
    """
    return base64.b64decode(base64_string)


def get_dimensions(image_bytes: bytes) -> Optional[Tuple[int, int]]:
    """
    Extract width and height from image bytes.
    
    Args:
        image_bytes: Raw image data
        
    Returns:
        Optional[Tuple[int, int]]: (width, height) or None if extraction failed
    """
    try:
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as img:
            return img.size
    except ImportError:
        logger.warning("PIL not available, cannot extract image dimensions")
        return None
    except Exception as e:
        logger.error(f"Failed to extract dimensions: {e}")
        return None


def get_format(image_bytes: bytes) -> Optional[str]:
    """
    Detect image format from bytes.
    
    Args:
        image_bytes: Raw image data
        
    Returns:
        Optional[str]: Format string (e.g., 'PNG', 'JPEG') or None if detection failed
    """
    try:
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as img:
            return img.format.lower() if img.format else None
    except ImportError:
        logger.warning("PIL not available, cannot detect image format")
        return None
    except Exception as e:
        logger.error(f"Failed to detect format: {e}")
        return None


def extract_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract comprehensive metadata from image bytes.
    
    Args:
        image_bytes: Raw image data
        
    Returns:
        Dict[str, Any]: Metadata including width, height, format, mode, size
    """
    metadata = {
        "size_bytes": len(image_bytes),
    }
    
    try:
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            metadata.update({
                "width": width,
                "height": height,
                "format": img.format.lower() if img.format else "unknown",
                "mode": img.mode,
            })
    except ImportError:
        logger.warning("PIL not available, limited metadata extraction")
    except Exception as e:
        logger.error(f"Failed to extract metadata: {e}")
        metadata["error"] = str(e)
    
    return metadata


def convert_format(image_bytes: bytes, 
                   target_format: str, 
                   quality: int = 90) -> Optional[bytes]:
    """
    Convert image to a different format.
    
    Args:
        image_bytes: Raw image data
        target_format: Target format (e.g., 'PNG', 'JPEG')
        quality: Quality setting for lossy formats (0-100)
        
    Returns:
        Optional[bytes]: Converted image data or None if conversion failed
    """
    try:
        from PIL import Image
        
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert to RGB if saving as JPEG and not already RGB
            if target_format.upper() in ['JPG', 'JPEG'] and img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes buffer
            output = io.BytesIO()
            img.save(output, format=target_format.upper(), quality=quality)
            return output.getvalue()
            
    except ImportError:
        logger.error("PIL not available, cannot convert image")
        return None
    except Exception as e:
        logger.error(f"Failed to convert image to {target_format}: {e}")
        return None


def resize_image(image_bytes: bytes,
                width: int,
                height: int,
                keep_aspect_ratio: bool = True,
                output_format: Optional[str] = None) -> Optional[bytes]:
    """
    Resize image to specified dimensions.
    
    Args:
        image_bytes: Raw image data
        width: Target width in pixels
        height: Target height in pixels
        keep_aspect_ratio: Whether to maintain aspect ratio
        output_format: Output format (e.g., 'PNG', 'JPEG'), defaults to original
        
    Returns:
        Optional[bytes]: Resized image data or None if resizing failed
    """
    try:
        from PIL import Image
        
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Calculate dimensions if keeping aspect ratio
            if keep_aspect_ratio:
                orig_width, orig_height = img.size
                aspect = orig_width / orig_height
                
                if width / height > aspect:
                    width = int(height * aspect)
                else:
                    height = int(width / aspect)
            
            # Resize the image
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Determine output format
            if output_format is None:
                output_format = img.format or 'PNG'
            
            # Convert to RGB if saving as JPEG
            if output_format.upper() in ['JPG', 'JPEG'] and resized.mode != 'RGB':
                resized = resized.convert('RGB')
            
            # Save to bytes buffer
            output = io.BytesIO()
            resized.save(output, format=output_format.upper())
            return output.getvalue()
            
    except ImportError:
        logger.error("PIL not available, cannot resize image")
        return None
    except Exception as e:
        logger.error(f"Failed to resize image: {e}")
        return None


def create_thumbnail(image_bytes: bytes,
                    max_size: int = 256,
                    output_format: str = 'PNG') -> Optional[bytes]:
    """
    Create a thumbnail from an image.
    
    Maintains aspect ratio and ensures neither dimension exceeds max_size.
    
    Args:
        image_bytes: Raw image data
        max_size: Maximum dimension (width or height) in pixels
        output_format: Output format (e.g., 'PNG', 'JPEG')
        
    Returns:
        Optional[bytes]: Thumbnail data or None if creation failed
    """
    try:
        from PIL import Image
        
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Create thumbnail (maintains aspect ratio)
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to RGB if saving as JPEG
            if output_format.upper() in ['JPG', 'JPEG'] and img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes buffer
            output = io.BytesIO()
            img.save(output, format=output_format.upper())
            return output.getvalue()
            
    except ImportError:
        logger.error("PIL not available, cannot create thumbnail")
        return None
    except Exception as e:
        logger.error(f"Failed to create thumbnail: {e}")
        return None

