"""
File system repository for media files.

Stores files on disk with metadata JSON + optional content files.
No manifest needed - each file is self-contained.
"""

# External dependencies
import os
import json
import logging
import shutil
import tempfile
from typing import Optional, List, Dict, Any

# Internal dependencies
from .base import FileRepository
from ..models import BaseFile, TextFile, ImageFile, AudioFile, Prompt, Conversation


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                     FILE SYSTEM REPOSITORY                           #
########################################################################
class FileSystemRepository(FileRepository):
    """
    File system implementation of FileRepository.

    Storage structure:
        base_directory/
          ├── texts/
          │   ├── {file_id}.json     (metadata + small content inline)
          ├── images/
          │   ├── {file_id}.json     (metadata only)
          │   └── {file_id}.png      (actual image data)
          ├── audio/
          │   ├── {file_id}.json
          │   └── {file_id}.mp3
          ├── prompts/
          │   └── {file_id}.json
          └── conversations/
              └── {file_id}.json

    Strategy:
    - Small files (text, prompts, conversations): inline content in JSON
    - Large files (images, audio): separate data files
    """

    # Size threshold for inlining content (10KB)
    INLINE_THRESHOLD = 10 * 1024

    def __init__(self, base_directory: str):
        """
        Initialize the file system repository.

        Args:
            base_directory: Base directory for storing files
        """
        self.base_directory = base_directory
        
        # Ensure base directory exists
        os.makedirs(self.base_directory, exist_ok=True)

    def _get_type_directory(self, file: BaseFile) -> str:
        """Get the subdirectory for a file type."""
        type_dirs = {
            'text': os.path.join(self.base_directory, 'texts'),
            'images': os.path.join(self.base_directory, 'images'),
            'audio': os.path.join(self.base_directory, 'audio'),
            'prompts': os.path.join(self.base_directory, 'prompts'),
            'conversations': os.path.join(self.base_directory, 'conversations'),
        }
        
        # Determine directory based on file type
        file_type = file.get_file_type().value
        dir_path = type_dirs.get(file_type, os.path.join(self.base_directory, file_type))
        
        # Ensure directory exists
        os.makedirs(dir_path, exist_ok=True)
        
        return dir_path

    def _get_metadata_path(self, file: BaseFile) -> str:
        """Get path to metadata JSON file."""
        type_dir = self._get_type_directory(file)
        return os.path.join(type_dir, f"{file.id}.json")

    def _get_content_path(self, file: BaseFile) -> str:
        """Get path to content file (for large files)."""
        type_dir = self._get_type_directory(file)
        
        # Get extension from filename
        ext = os.path.splitext(file.file_name)[1]
        if not ext:
            # Default extensions based on MIME type
            if file.mime_type.startswith('image/'):
                ext = '.jpg'
            elif file.mime_type.startswith('audio/'):
                ext = '.mp3'
            else:
                ext = '.dat'
        
        return os.path.join(type_dir, f"{file.id}{ext}")

    def _should_inline_content(self, file: BaseFile) -> bool:
        """Determine if content should be inlined in JSON."""
        # Always inline for prompts or conversations and if small enough, text files
        if isinstance(file, (Prompt, Conversation)):
            return True
        elif isinstance(file, TextFile):
            return file.size < self.INLINE_THRESHOLD
        
        # Never inline for binary files
        return False

    def save(self, file: BaseFile) -> bool:
        """
        Save a file to disk.

        Args:
            file: The file to save

        Returns:
            bool: True if save was successful
        """
        try:
            metadata_path = self._get_metadata_path(file)
            
            # Prepare metadata
            metadata = file.to_dict()
            
            # Handle content
            if file.has_content_loaded():
                if self._should_inline_content(file):
                    # Inline small text content
                    metadata['_inline_content'] = file._content
                else:
                    # Save large content separately
                    content_path = self._get_content_path(file)
                    self._save_content_file(file, content_path)
                    metadata['_content_file'] = os.path.basename(content_path)
            
            # Handle references
            if file.is_reference and file.source_path:
                metadata['_reference_source'] = file.source_path
            
            # Write metadata JSON atomically
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(metadata_path),
                suffix='.tmp',
                prefix=f'{file.id}_'
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                
                shutil.move(temp_path, metadata_path)
                logger.debug(f"Saved file {file.id} to {metadata_path}")
                return True
                
            except Exception as e:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e
        
        except Exception as e:
            logger.error(f"Failed to save file {file.id}: {e}")
            return False

    def _save_content_file(self, file: BaseFile, content_path: str) -> None:
        """Save content to a separate file."""
        content = file._content
        
        if isinstance(file, ImageFile):
            # Save PIL Image
            if content is not None:
                content.save(content_path)
        elif isinstance(file, (AudioFile,)):
            # Save binary data
            with open(content_path, 'wb') as f:
                f.write(content)
        elif isinstance(file, TextFile):
            # Save text
            with open(content_path, 'w', encoding=file.encoding) as f:
                f.write(content)
        else:
            # Generic binary save
            with open(content_path, 'wb') as f:
                if isinstance(content, str):
                    f.write(content.encode('utf-8'))
                else:
                    f.write(content)

    def load(self, file_id: str, load_content: bool = False) -> Optional[BaseFile]:
        """
        Load a file by ID.

        Args:
            file_id: The ID of the file to load
            load_content: Whether to load the file content

        Returns:
            Optional[BaseFile]: The loaded file, or None if not found
        """
        try:
            # Find the metadata file by searching all type directories
            metadata_path = self._find_metadata_file(file_id)
            
            if not metadata_path:
                logger.warning(f"File not found: {file_id}")
                return None
            
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Determine file type and create instance
            file = self._create_file_from_metadata(metadata)
            
            # Load content if requested
            if load_content:
                self._load_file_content(file, metadata, os.path.dirname(metadata_path))
            
            logger.debug(f"Loaded file {file_id}")
            return file
        
        except Exception as e:
            logger.error(f"Failed to load file {file_id}: {e}")
            return None

    def _find_metadata_file(self, file_id: str) -> Optional[str]:
        """Find metadata file across all type directories."""
        # Check all subdirectories (including any that might have been created)
        if not os.path.exists(self.base_directory):
            return None
        
        for entry in os.listdir(self.base_directory):
            entry_path = os.path.join(self.base_directory, entry)
            if os.path.isdir(entry_path):
                metadata_path = os.path.join(entry_path, f"{file_id}.json")
                if os.path.exists(metadata_path):
                    return metadata_path
        
        return None

    def _create_file_from_metadata(self, metadata: Dict[str, Any]) -> BaseFile:
        """Create appropriate file instance from metadata."""
        file_type = metadata.get('file_type', 'texts')
        
        if file_type == 'conversations':
            return Conversation.from_dict(metadata)
        elif file_type == 'prompts' or metadata.get('prompt_name'):
            return Prompt.from_dict(metadata)
        elif file_type == 'images':
            return ImageFile.from_dict(metadata)
        elif file_type == 'audio':
            return AudioFile.from_dict(metadata)
        else:
            return TextFile.from_dict(metadata)

    def _load_file_content(self, file: BaseFile, metadata: Dict[str, Any], type_dir: str) -> None:
        """Load content into file object."""
        # Check for inline content
        if '_inline_content' in metadata:
            file.set_content(metadata['_inline_content'])
            return
        
        # Check for content file
        if '_content_file' in metadata:
            content_path = os.path.join(type_dir, metadata['_content_file'])
            if os.path.exists(content_path):
                self._load_content_from_file(file, content_path)
                return
        
        # Handle references
        if file.is_reference and file.source_path:
            if file.is_url(file.source_path):
                # For URL references, don't auto-load
                logger.debug(f"File {file.id} is a URL reference, skipping content load")
            elif os.path.exists(file.source_path):
                # Load from referenced file
                self._load_content_from_file(file, file.source_path)
            else:
                logger.warning(f"Referenced file not found: {file.source_path}")

    def _load_content_from_file(self, file: BaseFile, content_path: str) -> None:
        """Load content from file path."""
        try:
            if isinstance(file, ImageFile):
                # Load PIL Image
                from PIL import Image
                img = Image.open(content_path)
                file.set_content(img)
            elif isinstance(file, AudioFile):
                # Load binary audio data
                with open(content_path, 'rb') as f:
                    file.set_content(f.read())
            elif isinstance(file, TextFile):
                # Load text
                with open(content_path, 'r', encoding=file.encoding) as f:
                    file.set_content(f.read())
            else:
                # Generic binary load
                with open(content_path, 'rb') as f:
                    file.set_content(f.read())
        except Exception as e:
            logger.error(f"Failed to load content from {content_path}: {e}")

    def delete(self, file_id: str) -> bool:
        """
        Delete a file.

        Args:
            file_id: The ID of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            # Find and load metadata to get content file path
            metadata_path = self._find_metadata_file(file_id)
            
            if not metadata_path:
                logger.warning(f"File not found for deletion: {file_id}")
                return False
            
            # Load metadata to find content file
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Delete content file if exists
            if '_content_file' in metadata:
                content_path = os.path.join(os.path.dirname(metadata_path), metadata['_content_file'])
                if os.path.exists(content_path):
                    os.remove(content_path)
            
            # Delete metadata file
            os.remove(metadata_path)
            
            logger.info(f"Deleted file {file_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def exists(self, file_id: str) -> bool:
        """Check if a file exists."""
        return self._find_metadata_file(file_id) is not None

    def list_all(self, file_type: Optional[str] = None) -> List[dict]:
        """
        List all files with metadata.

        Args:
            file_type: Optional filter by file type

        Returns:
            List[dict]: List of file metadata
        """
        try:
            files = []
            
            # Determine which directories to scan
            if file_type:
                subdirs = [file_type]
            else:
                subdirs = ['texts', 'images', 'audio', 'prompts', 'conversations']
            
            for subdir in subdirs:
                dir_path = os.path.join(self.base_directory, subdir)
                if not os.path.exists(dir_path):
                    continue
                
                for filename in os.listdir(dir_path):
                    if not filename.endswith('.json'):
                        continue
                    
                    try:
                        with open(os.path.join(dir_path, filename), 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        files.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to read {filename}: {e}")
            
            # Sort by updated_at
            files.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
            
            return files
        
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

