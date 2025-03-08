"""
This module contains the prompt store functionality for CLAIA.
It defines classes for managing and storing LLM prompts.
"""

# External dependencies
import os
import json
import uuid
from typing import Dict, Optional, List, Any

# Internal dependencies
from conversations.base import BaseFile



##################################################
#                PROMPT STORE                    #
##################################################
class Prompt(BaseFile):
  """
  Represents a reusable prompt template that can be used in conversations.
  """

  def __init__(self,
               base_directory: str,
               name: str,
               title: str,
               prompt: str,
               description: Optional[str] = None,
               prompt_id: Optional[str] = None):
    super().__init__(base_directory)
    self.prompt_id = prompt_id or str(uuid.uuid4())
    self.name = self.validate_and_format_name(name)
    self.title = title
    self.prompt = prompt
    self.description = description
    self.created_at = __import__('time').time()
    self.updated_at = self.created_at
    self.tags = []

  @staticmethod
  def validate_and_format_name(name: str) -> str:
    return name.lower().replace(' ', '-')

  def to_dict(self) -> Dict[str, Any]:
    return {
      "prompt_id": self.prompt_id,
      "name": self.name,
      "title": self.title,
      "prompt": self.prompt,
      "description": self.description,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      "tags": self.tags
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any], base_directory: str) -> 'Prompt':
    instance = cls(
      base_directory=base_directory,
      name=data["name"],
      title=data["title"],
      prompt=data["prompt"],
      description=data.get("description"),
      prompt_id=data["prompt_id"]
    )
    instance.created_at = data.get("created_at", instance.created_at)
    instance.updated_at = data.get("updated_at", instance.updated_at)
    instance.tags = data.get("tags", [])
    return instance

  def save(self):
    """Save the prompt to a file."""
    filename = f"{self.name}.json"
    filepath = os.path.join(self.base_directory, filename)

    with open(filepath, 'w') as f:
      json.dump(self.to_dict(), f, indent=2)

    return filepath

  @classmethod
  def load(cls, name: str, base_directory: str) -> 'Prompt':
    """Load a prompt by name."""
    filename = f"{name}.json"
    filepath = os.path.join(base_directory, filename)

    with open(filepath, 'r') as f:
      data = json.load(f)

    return cls.from_dict(data, base_directory)

  @classmethod
  def list_prompts(cls, base_directory: str) -> List[Dict[str, Any]]:
    """List all prompts in the directory."""
    prompts = []

    if not os.path.exists(base_directory):
      return prompts

    for filename in os.listdir(base_directory):
      if filename.endswith('.json'):
        filepath = os.path.join(base_directory, filename)
        try:
          with open(filepath, 'r') as f:
            data = json.load(f)
            prompts.append({
              "prompt_id": data.get("prompt_id"),
              "name": data.get("name"),
              "title": data.get("title"),
              "description": data.get("description"),
              "tags": data.get("tags", []),
              "updated_at": data.get("updated_at")
            })
        except Exception as e:
          print(f"Error loading prompt {filename}: {e}")

    # Sort by updated_at (newest first)
    prompts.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return prompts