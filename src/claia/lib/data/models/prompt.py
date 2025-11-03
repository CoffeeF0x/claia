"""
Prompt data model.

Special text file for prompts with validation and formatting.
"""

# External dependencies
import logging
import time
import re
from typing import Dict, Any, Optional

# Internal dependencies
from .text import TextFile


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                              PROMPT                                  #
########################################################################
class Prompt(TextFile):
    """
    Prompt model.

    Special text file for AI prompts with validation and formatting.
    Ensures prompt names follow conventions (lowercase with hyphens).
    """

    def __init__(self,
                 file_name: str,
                 prompt_name: Optional[str] = None,
                 prompt_type: str = "text",
                 **kwargs):
        """
        Initialize a prompt.

        Args:
            file_name: Name of the file (should end in .json)
            prompt_name: Validated name for the prompt
            prompt_type: Type of prompt (text, function, system, etc.)
            **kwargs: Additional arguments for TextFile
        """
        # Ensure JSON extension
        if not file_name.endswith('.json'):
            file_name = f"{file_name}.json"
        
        # Set JSON MIME type
        kwargs['mime_type'] = 'application/json'
        
        super().__init__(file_name=file_name, encoding='utf-8', **kwargs)
        
        # Prompt-specific fields
        self.prompt_name = self.validate_prompt_name(prompt_name) if prompt_name else self._extract_name_from_filename(file_name)
        self.prompt_type = prompt_type
        
        # Store in metadata
        self.metadata['prompt_name'] = self.prompt_name
        self.metadata['prompt_type'] = self.prompt_type

    def _extract_name_from_filename(self, file_name: str) -> str:
        """Extract prompt name from filename."""
        name = file_name.replace('.json', '')
        return self.validate_prompt_name(name)

    def get_file_type(self):
        """Override to return PROMPT file type instead of TEXT."""
        from ...enums.file import FileSubdirectory
        return FileSubdirectory.PROMPT

    @staticmethod
    def validate_prompt_name(name: str) -> str:
        """
        Validate and format a prompt name to be lowercase with hyphens.

        Args:
            name: Prompt name to validate

        Returns:
            str: Validated prompt name (lowercase with hyphens)
        """
        if not name:
            return "untitled-prompt"

        # Convert to lowercase
        name = name.lower()

        # Replace spaces with hyphens
        name = re.sub(r'\s+', '-', name)

        # Remove any characters that aren't alphanumeric or hyphens
        name = re.sub(r'[^a-z0-9-]', '', name)

        # Replace multiple consecutive hyphens with a single hyphen
        name = re.sub(r'-+', '-', name)

        # Remove leading/trailing hyphens
        name = name.strip('-')

        return name or "untitled-prompt"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data['prompt_name'] = self.prompt_name
        data['prompt_type'] = self.prompt_type
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prompt':
        """
        Create prompt from dictionary.

        Args:
            data: Dictionary containing prompt data

        Returns:
            Prompt: New prompt instance
        """
        return cls(
            file_name=data.get('file_name', 'untitled-prompt.json'),
            file_id=data.get('id'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_path=data.get('source_path'),
            prompt_name=data.get('prompt_name') or data.get('metadata', {}).get('prompt_name'),
            prompt_type=data.get('prompt_type', 'text') or data.get('metadata', {}).get('prompt_type'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    @classmethod
    def from_content(cls, content: str, prompt_name: str, prompt_type: str = "text", **kwargs) -> 'Prompt':
        """
        Create a prompt from content.

        Args:
            content: The prompt text
            prompt_name: Name for the prompt
            prompt_type: Type of prompt
            **kwargs: Additional arguments

        Returns:
            Prompt: New prompt with content set
        """
        # Validate and create filename
        validated_name = cls.validate_prompt_name(prompt_name)
        file_name = kwargs.pop('file_name', f"{validated_name}.json")
        
        prompt = cls(
            file_name=file_name,
            prompt_name=validated_name,
            prompt_type=prompt_type,
            **kwargs
        )
        
        prompt._content = content
        prompt._content_loaded = True
        prompt.size = len(content.encode('utf-8'))
        prompt.updated_at = time.time()
        
        return prompt

    @classmethod
    def from_path(cls, source: str, is_reference: bool = False, **kwargs) -> 'Prompt':
        """
        Create a prompt referencing a path.

        Args:
            source: Path to the file
            is_reference: Whether to just reference (True) or import (False)
            **kwargs: Additional arguments

        Returns:
            Prompt: New prompt instance
        """
        import os
        
        file_name = kwargs.pop('file_name', os.path.basename(source))
        if not file_name.endswith('.json'):
            file_name = f"{file_name}.json"
        
        # Extract prompt name from filename if not provided
        prompt_name = kwargs.pop('prompt_name', file_name.replace('.json', ''))
        
        return cls(
            file_name=file_name,
            is_reference=is_reference,
            source_path=source,
            prompt_name=prompt_name,
            **kwargs
        )

