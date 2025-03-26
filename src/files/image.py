"""
This module contains the image file handling class for CLAIA.
"""

# External dependencies
import os
import base64
import logging
import io
from typing import Dict, Any, Optional, Type, TypeVar, Union, Tuple

# Internal dependencies
from .base import BaseFile



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods
T = TypeVar('T', bound='ImageFile')



########################################################################
#                              IMAGEFILE                               #
########################################################################
class ImageFile(BaseFile):
  """
  Class for handling image files.
  
  Provides functionality specific to image files, including:
  - Extracting image metadata (dimensions, format)
  - Converting between image formats
  - Generating base64 encoded versions for display
  """
  
  def __init__(self, base_directory: str, **kwargs):
    """
    Initialize an ImageFile object.
    
    Args:
      base_directory: Base directory for file storage
      **kwargs: Additional arguments to pass to the parent class
                (file_name, external_path, is_reference, file_id,
                 mime_type, timestamp, metadata, etc.)
    """
    # Ensure metadata is initialized if not provided
    if 'metadata' in kwargs:
      kwargs['metadata'] = kwargs['metadata'] or {}
    
    # Pass all arguments to the parent class
    super().__init__(base_directory=base_directory, **kwargs)
    
    # Image-specific attributes
    self.width = self.metadata.get("width", 0)
    self.height = self.metadata.get("height", 0)
    self.format = self.metadata.get("format", "")
    
    # If format is not set, try to determine it from file extension
    if not self.format and self.file_name:
      self.format = os.path.splitext(self.file_name)[1].lstrip('.').lower()
  
  @classmethod
  def from_bytes(cls, 
                 image_data: bytes, 
                 base_directory: str, 
                 file_name: str, 
                 format: str = "png", 
                 mime_type: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None) -> T:
    """
    Create an ImageFile from binary image data.
    
    Args:
      image_data: The binary image data
      base_directory: Base directory for file storage
      file_name: Name for the file
      format: Image format (png, jpg, etc.)
      mime_type: Optional MIME type (detected if not provided)
      metadata: Optional additional metadata for the file
      
    Returns:
      ImageFile: A new ImageFile instance
    """
    try:
      # Get image dimensions if PIL is available
      width = 0
      height = 0
      try:
        from PIL import Image
        with Image.open(io.BytesIO(image_data)) as img:
          width, height = img.size
      except ImportError:
        logger.warning("PIL not available, cannot extract image dimensions")
      
      # Set proper mime type
      if mime_type is None:
        mime_type = f"image/{format}"
      
      # Create additional metadata
      combined_metadata = {
        "width": width,
        "height": height,
        "format": format,
        "source": "in_memory"
      }
      
      # Merge with provided metadata
      if metadata:
        combined_metadata.update(metadata)
      
      # Use the base class implementation to handle file creation
      image = super().from_content(
        content=image_data,
        base_directory=base_directory,
        file_name=file_name,
        mime_type=mime_type,
        metadata=combined_metadata
      )
      
      if image:
        # Process to update metadata
        image.process()
      
      return image
    except Exception as e:
      logger.error(f"Failed to create image from bytes: {e}")
      raise
  
  def process(self) -> Dict[str, Any]:
    """
    Process the image file and extract its metadata.
    
    Returns:
      Dict[str, Any]: The extracted metadata
    """
    if not self.file_exists():
      return {"error": "File does not exist"}
    
    try:
      # Try to get image dimensions using PIL if available
      try:
        from PIL import Image
        with Image.open(self.path) as img:
          self.width, self.height = img.size
          self.format = img.format.lower() if img.format else self.format
      except ImportError:
        logger.warning("PIL not available, cannot extract image dimensions")
      
      # Update metadata
      self.metadata.update({
        "width": self.width,
        "height": self.height,
        "format": self.format,
        "size_bytes": self.get_file_size()
      })
      
      # Save updated metadata
      self.save_metadata()
      
      return {
        "width": self.width,
        "height": self.height,
        "format": self.format,
        "size_bytes": self.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process image {self.file_id}: {e}")
      return {"error": str(e)}
  
  def get_base64(self) -> Optional[str]:
    """
    Get the image as a base64-encoded string.
    
    Returns:
      Optional[str]: Base64-encoded image data, or None if encoding failed
    """
    if not self.file_exists():
      return None
    
    try:
      with open(self.path, 'rb') as f:
        image_data = f.read()
      
      return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
      logger.error(f"Failed to encode image {self.file_id} as base64: {e}")
      return None
  
  def convert(self, target_format: str, quality: int = 90) -> Optional['ImageFile']:
    """
    Convert the image to a different format.
    
    Args:
      target_format: Format to convert to (jpg, png, etc.)
      quality: Quality setting for lossy formats (0-100)
      
    Returns:
      Optional[ImageFile]: New ImageFile with the converted format, or None if conversion failed
    """
    if not self.file_exists():
      logger.error(f"Cannot convert non-existent image {self.file_id}")
      return None
    
    try:
      from PIL import Image
      
      # Create a new file ID for the converted image
      new_file_id = f"{self.file_id}_converted_{target_format}"
      new_file_name = f"{os.path.splitext(self.file_name)[0]}.{target_format}"
      
      # Create output path directly to a temporary location first
      import tempfile
      temp_output = tempfile.mktemp(suffix=f".{target_format}")
      
      # Open and convert the image
      with Image.open(self.path) as img:
        # Convert image to RGB if saving as JPEG and it's not already RGB
        if target_format.lower() in ['jpg', 'jpeg'] and img.mode != 'RGB':
          img = img.convert('RGB')
        
        # Save in the new format to the temporary location
        img.save(temp_output, format=target_format.upper(), quality=quality)
      
      # Create a new ImageFile for the converted image
      converted = ImageFile(
        base_directory=self.base_directory,
        file_name=new_file_name,
        file_id=new_file_id,
        source_path=temp_output,  # Use the temp file as the source path
        mime_type=f"image/{target_format.lower()}",
        metadata={
          "width": self.width,
          "height": self.height,
          "format": target_format.lower(),
          "original_file_id": self.file_id
        }
      )
      
      # Process to update metadata
      converted.process()
      converted.save()
      
      # Clean up the temporary file
      try:
        os.remove(temp_output)
      except:
        pass
      
      return converted
    except ImportError:
      logger.error("PIL not available, cannot convert image")
      return None
    except Exception as e:
      logger.error(f"Failed to convert image {self.file_id} to {target_format}: {e}")
      return None
  
  def resize(self, width: int, height: int, keep_aspect_ratio: bool = True) -> Optional['ImageFile']:
    """
    Resize the image to the specified dimensions.
    
    Args:
      width: Target width in pixels
      height: Target height in pixels
      keep_aspect_ratio: Whether to maintain the aspect ratio
      
    Returns:
      Optional[ImageFile]: New ImageFile with the resized image, or None if resizing failed
    """
    if not self.file_exists():
      logger.error(f"Cannot resize non-existent image {self.file_id}")
      return None
    
    try:
      from PIL import Image
      
      # Open the image
      with Image.open(self.path) as img:
        # Calculate dimensions if keeping aspect ratio
        if keep_aspect_ratio:
          orig_width, orig_height = img.size
          aspect = orig_width / orig_height
          
          if width / height > aspect:
            # Width would be too big
            width = int(height * aspect)
          else:
            # Height would be too big
            height = int(width / aspect)
        
        # Resize the image
        resized_img = img.resize((width, height))
        
        # Create a temporary file for the resized image
        import tempfile
        ext = os.path.splitext(self.file_name)[1] or ".png"
        temp_output = tempfile.mktemp(suffix=ext)
        
        # Save the resized image
        resized_img.save(temp_output)
        
        # Create a new file name based on dimensions
        new_file_name = f"{os.path.splitext(self.file_name)[0]}_{width}x{height}{ext}"
        
        # Create a new ImageFile for the resized image
        resized_file = ImageFile(
          base_directory=self.base_directory,
          file_name=new_file_name,
          source_path=temp_output,  # Use the temp file as the source path
          mime_type=self.mime_type,
          metadata={
            "width": width,
            "height": height,
            "format": self.format,
            "original_file_id": self.file_id,
            "resized_from": self.path
          }
        )
      
      # Save the file to storage
      resized_file.save()
      
      # Clean up the temporary file
      try:
        os.remove(temp_output)
      except:
        pass
      
      return resized_file
    except ImportError:
      logger.error("PIL not available, cannot resize image")
      return None
    except Exception as e:
      logger.error(f"Failed to resize image {self.file_id}: {e}")
      return None