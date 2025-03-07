"""
This module contains the prompt store functionality for CLAIA.
It defines classes for managing and storing LLM prompts.
"""

# External dependencies
from typing import Dict, Optional

# Internal dependencies
from conversations.base import BaseFile



##################################################
#                PROMPT STORE                    #
##################################################
class LLMPromptStore(BaseFile):
  def __init__(self, base_directory: str, name: str, title: str, prompt: str, description: Optional[str] = None):
    super().__init__(base_directory)
    self.name = name
    self.title = title
    self.prompt = prompt
    self.description = description

  @staticmethod
  def validate_and_format_name(name: str) -> str:
    return name.lower().replace(' ', '-')

  def to_dict(self) -> Dict:
    return {
      "unique_id": self.unique_id,
      "name": self.name,
      "title": self.title,
      "prompt": self.prompt,
      "description": self.description
    }

  @classmethod
  def from_dict(cls, data: Dict, base_directory: str):
    instance = cls(
      base_directory=base_directory,
      name=data["name"],
      title=data["title"],
      prompt=data["prompt"],
      description=data.get("description")
    )
    instance.unique_id = data["unique_id"]
    return instance