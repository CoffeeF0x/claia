import json
import os
import uuid
from typing import Dict, List, Optional



##################################################
#                  BASE CLASS                    #
##################################################
class BaseFile:
  def __init__(self, base_directory: str):
    self.base_directory = base_directory
    self.unique_id = str(uuid.uuid4())
    self.ensure_directory_exists()

  def ensure_directory_exists(self):
    os.makedirs(self.base_directory, exist_ok=True)

  def save(self, filename: str):
    full_path = os.path.join(self.base_directory, filename)
    with open(full_path, 'w') as file:
      json.dump(self.to_dict(), file, indent=2)

  @classmethod
  def load(cls, filename: str, base_directory: str):
    full_path = os.path.join(base_directory, filename)
    with open(full_path, 'r') as file:
      data = json.load(file)
    return cls.from_dict(data, base_directory)

  def to_dict(self) -> Dict:
    raise NotImplementedError("Subclasses must implement to_dict method")

  @classmethod
  def from_dict(cls, data: Dict, base_directory: str):
    raise NotImplementedError("Subclasses must implement from_dict method")

  @staticmethod
  def list_files(directory: str) -> List[str]:
    return [f for f in os.listdir(directory) if f.endswith('.json')]



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
