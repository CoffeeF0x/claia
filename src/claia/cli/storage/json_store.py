"""
Simple JSON file storage for the CLI.

Saves artifacts (conversations, prompts, etc.) as JSON files organized
into type-based subdirectories. This is the only persistence the CLI needs —
objects that aren't saved to files simply live in memory as Python objects.
"""

import json
import logging
import os
import shutil
import tempfile
from typing import Optional, List, Dict, Any, Union

from claia.core.data import (
  BaseArtifact,
  TextArtifact,
  ImageArtifact,
  AudioArtifact,
  FileArtifact,
  LinkArtifact,
  RawArtifact,
  Prompt,
  Conversation,
)

StoreObject = Union[BaseArtifact, Prompt, Conversation]

logger = logging.getLogger(__name__)


class JsonStore:
    """
    Saves and loads artifacts as JSON files.

    Storage layout:
        base_directory/
          ├── texts/         (.json per artifact)
          ├── images/        (.json per artifact)
          ├── audio/         (.json per artifact)
          ├── prompts/       (.json per artifact)
          └── conversations/ (.json per artifact)
    """

    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        os.makedirs(self.base_directory, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _subdir_for(self, artifact: StoreObject) -> str:
        if isinstance(artifact, Conversation):
            return "conversations"
        if isinstance(artifact, Prompt):
            return "prompts"
        if isinstance(artifact, ImageArtifact):
            return "images"
        if isinstance(artifact, AudioArtifact):
            return "audio"
        if isinstance(artifact, (FileArtifact, LinkArtifact, RawArtifact)):
            return "files"
        return "texts"

    def _ensure_dir(self, subdir: str) -> str:
        path = os.path.join(self.base_directory, subdir)
        os.makedirs(path, exist_ok=True)
        return path

    def _find_json(self, artifact_id: str) -> Optional[str]:
        """Locate the JSON file for an artifact across all subdirectories."""
        if not os.path.exists(self.base_directory):
            return None
        for entry in os.listdir(self.base_directory):
            candidate = os.path.join(self.base_directory, entry, f"{artifact_id}.json")
            if os.path.isdir(os.path.join(self.base_directory, entry)) and os.path.exists(candidate):
                return candidate
        return None

    def _artifact_from_dict(self, data: Dict[str, Any]) -> StoreObject:
        """Rehydrate a typed object from a raw dict."""
        atype = data.get("artifact_type", "texts")
        if atype == "conversations":
            return Conversation.from_dict(data)
        if atype == "prompts" or data.get("prompt_name"):
            return Prompt.from_dict(data)
        if atype == "images":
            return ImageArtifact.from_dict(data)
        if atype == "audio":
            return AudioArtifact.from_dict(data)
        if atype == "files":
            if data.get("uri") is not None or data.get("format") == "uri-list":
                return LinkArtifact.from_dict(data)
            if data.get("format") == "octet-stream":
                return RawArtifact.from_dict(data)
            return FileArtifact.from_dict(data)
        return TextArtifact.from_dict(data)

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def save(self, artifact: StoreObject) -> bool:
        """Serialize an artifact/prompt/conversation to a JSON file."""
        try:
            subdir = self._subdir_for(artifact)
            dir_path = self._ensure_dir(subdir)
            object_id = getattr(artifact, "id", None) or getattr(artifact, "guid")
            dest = os.path.join(dir_path, f"{object_id}.json")

            data = artifact.to_dict()
            data["artifact_type"] = subdir

            fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp", prefix=f"{object_id}_")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                shutil.move(tmp, dest)
                return True
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")
            return False

    def load(self, artifact_id: str) -> Optional[StoreObject]:
        """Load an artifact by ID from any subdirectory."""
        try:
            path = self._find_json(artifact_id)
            if not path:
                return None
            with open(path, "r", encoding="utf-8") as f:
                return self._artifact_from_dict(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load artifact {artifact_id}: {e}")
            return None

    def delete(self, artifact_id: str) -> bool:
        """Delete the JSON file for an artifact."""
        try:
            path = self._find_json(artifact_id)
            if not path:
                return False
            os.remove(path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete artifact {artifact_id}: {e}")
            return False

    def exists(self, artifact_id: str) -> bool:
        return self._find_json(artifact_id) is not None

    def list_all(self, artifact_type: Optional[str] = None) -> List[dict]:
        """List metadata dicts for all artifacts, optionally filtered by type."""
        try:
            results: List[dict] = []
            subdirs = [artifact_type] if artifact_type else [
                "texts", "images", "audio", "files", "prompts", "conversations",
            ]
            for subdir in subdirs:
                dir_path = os.path.join(self.base_directory, subdir)
                if not os.path.isdir(dir_path):
                    continue
                for fname in os.listdir(dir_path):
                    if not fname.endswith(".json"):
                        continue
                    try:
                        with open(os.path.join(dir_path, fname), "r", encoding="utf-8") as f:
                            results.append(json.load(f))
                    except Exception as e:
                        logger.warning(f"Failed to read {fname}: {e}")
            results.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            return results
        except Exception as e:
            logger.error(f"Failed to list artifacts: {e}")
            return []
