"""
Prompt data model.

Specialized text artifact for prompts with validation and formatting.
"""

import logging
import time
import re
from typing import Dict, Any, Optional

from .text import TextArtifact


logger = logging.getLogger(__name__)


class Prompt(TextArtifact):
    """
    Prompt model.

    Specialized text artifact for AI prompts with validation and formatting.
    Ensures prompt names follow conventions (lowercase with hyphens).
    """

    def __init__(self,
                 name: str = "untitled-prompt.json",
                 prompt_name: Optional[str] = None,
                 prompt_type: str = "text",
                 **kwargs):
        if not name.endswith('.json'):
            name = f"{name}.json"

        kwargs['media_type'] = 'application/json'

        super().__init__(name=name, encoding='utf-8', **kwargs)

        self.prompt_name = self.validate_prompt_name(prompt_name) if prompt_name else self._extract_name(name)
        self.prompt_type = prompt_type
        self.metadata['prompt_name'] = self.prompt_name
        self.metadata['prompt_type'] = self.prompt_type

    def _extract_name(self, name: str) -> str:
        return self.validate_prompt_name(name.replace('.json', ''))

    @staticmethod
    def validate_prompt_name(name: str) -> str:
        if not name:
            return "untitled-prompt"
        name = name.lower()
        name = re.sub(r'\s+', '-', name)
        name = re.sub(r'[^a-z0-9-]', '', name)
        name = re.sub(r'-+', '-', name)
        name = name.strip('-')
        return name or "untitled-prompt"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['prompt_name'] = self.prompt_name
        data['prompt_type'] = self.prompt_type
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prompt':
        return cls(
            name=data.get('name', 'untitled-prompt.json'),
            id=data.get('id'),
            size=data.get('size', 0),
            is_reference=data.get('is_reference', False),
            source_uri=data.get('source_uri'),
            prompt_name=data.get('prompt_name') or data.get('metadata', {}).get('prompt_name'),
            prompt_type=data.get('prompt_type', 'text') or data.get('metadata', {}).get('prompt_type'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    @classmethod
    def from_content(cls, content: str, prompt_name: str, prompt_type: str = "text", **kwargs) -> 'Prompt':
        validated_name = cls.validate_prompt_name(prompt_name)
        name = kwargs.pop('name', f"{validated_name}.json")

        prompt = cls(
            name=name,
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
        import os
        name = kwargs.pop('name', os.path.basename(source))
        if not name.endswith('.json'):
            name = f"{name}.json"
        prompt_name = kwargs.pop('prompt_name', name.replace('.json', ''))
        return cls(
            name=name,
            is_reference=is_reference,
            source_uri=source,
            prompt_name=prompt_name,
            **kwargs
        )
