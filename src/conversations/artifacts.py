"""
This module contains the artifact management system for CLAIA.
Artifacts are persistent files that can be referenced across conversations.
"""

# External dependencies
import os
import shutil
import json
import uuid
import logging
from typing import Dict, List, Any, Optional

# Internal dependencies
from conversations.base import BaseFile
from conversations.files import FileReference, FileHandler



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              ARTIFACTS                               #
########################################################################
class Artifact(BaseFile):
  """
  Represents a persistent file artifact that can be referenced across conversations.
  """

  def __init__(self,
               base_directory: str,
               name: str,
               file_path: str,
               artifact_id: Optional[str] = None,
               description: Optional[str] = None):
    super().__init__(base_directory)
    self.artifact_id = artifact_id or str(uuid.uuid4())
    self.name = name
    self.description = description
    self.versions: List[ArtifactVersion] = []

    # Create the first version from the provided file
    self.add_version(file_path)

  def add_version(self, file_path: str, message: Optional[str] = None) -> 'ArtifactVersion':
    """
    Add a new version of this artifact.

    Args:
        file_path: The path to the file to add as a new version
        message: An optional message describing the version

    Returns:
        ArtifactVersion: The created version
    """
    # Create artifact directory if it doesn't exist
    artifact_dir = os.path.join(self.base_directory, self.artifact_id)
    self.ensure_directory(artifact_dir)

    # Create a new version
    version_number = len(self.versions) + 1
    version = ArtifactVersion(
      version_number=version_number,
      original_file_path=file_path,
      message=message or f"Version {version_number}"
    )

    # Copy the file to the artifact directory
    version_file_name = f"v{version_number}_{os.path.basename(file_path)}"
    version_path = os.path.join(artifact_dir, version_file_name)

    try:
      shutil.copy2(file_path, version_path)
      version.stored_file_path = version_path

      # Add the version to our list
      self.versions.append(version)
      return version
    except Exception as e:
      logger.error(f"Failed to copy file {file_path} to {version_path}: {e}")
      raise

  def get_latest_version(self) -> Optional['ArtifactVersion']:
    """
    Get the latest version of this artifact.

    Returns:
        Optional[ArtifactVersion]: The latest version, or None if no versions exist
    """
    if not self.versions:
      return None
    return self.versions[-1]

  def get_file_reference(self) -> FileReference:
    """
    Get a file reference to the latest version of this artifact.

    Returns:
        FileReference: A file reference to the latest version

    Raises:
        ValueError: If the artifact has no versions
    """
    latest = self.get_latest_version()
    if not latest:
      raise ValueError("Artifact has no versions")

    return FileReference(
      file_path=latest.stored_file_path,
      file_id=f"{self.artifact_id}_v{latest.version_number}"
    )

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the artifact to a dictionary.

    Returns:
        Dict[str, Any]: The artifact as a dictionary
    """
    return {
      "artifact_id": self.artifact_id,
      "name": self.name,
      "description": self.description,
      "versions": [v.to_dict() for v in self.versions],
      "base_directory": self.base_directory
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any], base_directory: str) -> 'Artifact':
    """
    Create an artifact from a dictionary.

    Args:
        data: The dictionary containing the artifact data
        base_directory: The base directory for file operations

    Returns:
        Artifact: The created artifact
    """
    artifact = cls(
      base_directory=base_directory,
      name=data["name"],
      file_path=data["versions"][-1]["stored_file_path"],  # Use the latest version
      artifact_id=data["artifact_id"],
      description=data.get("description")
    )

    # Clear the versions list (since init added the first version)
    artifact.versions = []

    # Add all versions from the data
    for version_data in data["versions"]:
      version = ArtifactVersion.from_dict(version_data)
      artifact.versions.append(version)

    return artifact

  def save(self) -> Optional[str]:
    """
    Save the artifact metadata.

    Returns:
        Optional[str]: The path to the saved metadata file, or None if saving failed
    """
    artifact_dir = os.path.join(self.base_directory, self.artifact_id)
    self.ensure_directory(artifact_dir)

    metadata_path = os.path.join(artifact_dir, "metadata.json")
    try:
      with open(metadata_path, 'w') as f:
        json.dump(self.to_dict(), f, indent=2)
      return metadata_path
    except Exception as e:
      logger.error(f"Failed to save artifact metadata: {e}")
      return None

  @classmethod
  def load(cls, artifact_id: str, base_directory: str) -> Optional['Artifact']:
    """
    Load an artifact from its ID.

    Args:
        artifact_id: The ID of the artifact to load
        base_directory: The base directory for file operations

    Returns:
        Optional[Artifact]: The loaded artifact, or None if loading failed
    """
    metadata_path = os.path.join(base_directory, artifact_id, "metadata.json")
    try:
      if not os.path.exists(metadata_path):
        logger.error(f"Artifact metadata file {metadata_path} does not exist")
        return None

      with open(metadata_path, 'r') as f:
        data = json.load(f)
      return cls.from_dict(data, base_directory)
    except Exception as e:
      logger.error(f"Failed to load artifact {artifact_id}: {e}")
      return None

  @classmethod
  def list_artifacts(cls, base_directory: str) -> List[Dict[str, Any]]:
    """
    List all artifacts in the directory.

    Args:
        base_directory: The base directory for file operations

    Returns:
        List[Dict[str, Any]]: A list of artifact metadata
    """
    artifacts = []

    if not os.path.exists(base_directory):
      logger.warning(f"Artifacts directory {base_directory} does not exist")
      return artifacts

    for item in os.listdir(base_directory):
      item_path = os.path.join(base_directory, item)
      if os.path.isdir(item_path):
        metadata_path = os.path.join(item_path, "metadata.json")
        if os.path.exists(metadata_path):
          try:
            with open(metadata_path, 'r') as f:
              data = json.load(f)
              artifacts.append({
                "artifact_id": data.get("artifact_id"),
                "name": data.get("name"),
                "description": data.get("description"),
                "version_count": len(data.get("versions", []))
              })
          except Exception as e:
            logger.error(f"Error loading artifact {item}: {e}")

    return artifacts


class ArtifactVersion:
  """Represents a specific version of an artifact."""

  def __init__(self,
               version_number: int,
               original_file_path: str,
               message: str,
               stored_file_path: Optional[str] = None):
    self.version_number = version_number
    self.original_file_path = original_file_path
    self.stored_file_path = stored_file_path
    self.message = message
    self.timestamp = __import__('time').time()

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the artifact version to a dictionary.

    Returns:
        Dict[str, Any]: The artifact version as a dictionary
    """
    return {
      "version_number": self.version_number,
      "original_file_path": self.original_file_path,
      "stored_file_path": self.stored_file_path,
      "message": self.message,
      "timestamp": self.timestamp
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'ArtifactVersion':
    """
    Create an artifact version from a dictionary.

    Args:
        data: The dictionary containing the artifact version data

    Returns:
        ArtifactVersion: The created artifact version
    """
    return cls(
      version_number=data["version_number"],
      original_file_path=data["original_file_path"],
      stored_file_path=data["stored_file_path"],
      message=data["message"]
    )