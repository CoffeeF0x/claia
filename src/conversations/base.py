"""
This module contains the base file handling functionality for CLAIA.
It defines the base class for file operations used throughout the application.
"""

# External dependencies
import json
import os
import uuid
from typing import Dict, List



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