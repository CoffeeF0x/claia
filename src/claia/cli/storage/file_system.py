"""
File system storage for CLI artifacts.

Stores artifacts on disk with JSON metadata and optional detached content files.
"""

import json
import logging
import os
import shutil
import tempfile
from typing import Optional, List, Dict, Any

from .base import ArtifactStore
from claia.lib.data.models import (
    BaseArtifact,
    TextArtifact,
    ImageArtifact,
    AudioArtifact,
    Prompt,
    Conversation,
)

logger = logging.getLogger(__name__)


class FileSystemStore(ArtifactStore):
    """
    File system implementation of ArtifactStore.

    Storage structure:
        base_directory/
          ├── texts/
          ├── images/
          ├── audio/
          ├── prompts/
          └── conversations/
    """

    INLINE_THRESHOLD = 10 * 1024

    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        os.makedirs(self.base_directory, exist_ok=True)

    def _resolve_subdir(self, artifact: BaseArtifact) -> str:
        """Determine the storage subdirectory based on artifact type."""
        if isinstance(artifact, Conversation):
            return "conversations"
        if isinstance(artifact, Prompt):
            return "prompts"
        if isinstance(artifact, ImageArtifact):
            return "images"
        if isinstance(artifact, AudioArtifact):
            return "audio"
        return "texts"

    def _get_type_directory(self, artifact: BaseArtifact) -> str:
        subdir = self._resolve_subdir(artifact)
        dir_path = os.path.join(self.base_directory, subdir)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def _get_metadata_path(self, artifact: BaseArtifact) -> str:
        type_dir = self._get_type_directory(artifact)
        return os.path.join(type_dir, f"{artifact.id}.json")

    def _get_content_path(self, artifact: BaseArtifact) -> str:
        type_dir = self._get_type_directory(artifact)
        ext = os.path.splitext(artifact.name)[1]
        if not ext:
            if artifact.media_type.startswith("image/"):
                ext = ".jpg"
            elif artifact.media_type.startswith("audio/"):
                ext = ".mp3"
            else:
                ext = ".dat"
        return os.path.join(type_dir, f"{artifact.id}{ext}")

    def _should_inline_content(self, artifact: BaseArtifact) -> bool:
        if isinstance(artifact, (Prompt, Conversation)):
            return True
        if isinstance(artifact, TextArtifact):
            return artifact.size < self.INLINE_THRESHOLD
        return False

    def save(self, artifact: BaseArtifact) -> bool:
        try:
            metadata_path = self._get_metadata_path(artifact)
            metadata = artifact.to_dict()

            # Tag with storage-level type hint for rehydration on load
            metadata["artifact_type"] = self._resolve_subdir(artifact)

            if artifact.has_content_loaded():
                if self._should_inline_content(artifact):
                    metadata["_inline_content"] = artifact._content
                else:
                    content_path = self._get_content_path(artifact)
                    self._save_content_file(artifact, content_path)
                    metadata["_content_file"] = os.path.basename(content_path)

            if artifact.is_reference and artifact.source_uri:
                metadata["_reference_source"] = artifact.source_uri

            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(metadata_path),
                suffix=".tmp",
                prefix=f"{artifact.id}_",
            )
            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                shutil.move(temp_path, metadata_path)
                return True
            except Exception:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise

        except Exception as e:
            logger.error(f"Failed to save artifact {artifact.id}: {e}")
            return False

    def _save_content_file(self, artifact: BaseArtifact, content_path: str) -> None:
        content = artifact._content
        if isinstance(artifact, ImageArtifact):
            if content is not None:
                content.save(content_path)
        elif isinstance(artifact, AudioArtifact):
            with open(content_path, "wb") as f:
                f.write(content)
        elif isinstance(artifact, TextArtifact):
            with open(content_path, "w", encoding=artifact.encoding) as f:
                f.write(content)
        else:
            with open(content_path, "wb") as f:
                if isinstance(content, str):
                    f.write(content.encode("utf-8"))
                else:
                    f.write(content)

    def load(self, artifact_id: str, load_content: bool = False) -> Optional[BaseArtifact]:
        try:
            metadata_path = self._find_metadata_file(artifact_id)
            if not metadata_path:
                return None

            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            artifact = self._create_artifact_from_metadata(metadata)
            if load_content:
                self._load_artifact_content(artifact, metadata, os.path.dirname(metadata_path))
            return artifact
        except Exception as e:
            logger.error(f"Failed to load artifact {artifact_id}: {e}")
            return None

    def _find_metadata_file(self, artifact_id: str) -> Optional[str]:
        if not os.path.exists(self.base_directory):
            return None
        for entry in os.listdir(self.base_directory):
            entry_path = os.path.join(self.base_directory, entry)
            if os.path.isdir(entry_path):
                metadata_path = os.path.join(entry_path, f"{artifact_id}.json")
                if os.path.exists(metadata_path):
                    return metadata_path
        return None

    def _create_artifact_from_metadata(self, metadata: Dict[str, Any]) -> BaseArtifact:
        artifact_type = metadata.get("artifact_type", "texts")
        if artifact_type == "conversations":
            return Conversation.from_dict(metadata)
        if artifact_type == "prompts" or metadata.get("prompt_name"):
            return Prompt.from_dict(metadata)
        if artifact_type == "images":
            return ImageArtifact.from_dict(metadata)
        if artifact_type == "audio":
            return AudioArtifact.from_dict(metadata)
        return TextArtifact.from_dict(metadata)

    def _load_artifact_content(self, artifact: BaseArtifact, metadata: Dict[str, Any], type_dir: str) -> None:
        if "_inline_content" in metadata:
            artifact.set_content(metadata["_inline_content"])
            return
        if "_content_file" in metadata:
            content_path = os.path.join(type_dir, metadata["_content_file"])
            if os.path.exists(content_path):
                self._load_content_from_file(artifact, content_path)
                return
        if artifact.is_reference and artifact.source_uri:
            if artifact.is_url(artifact.source_uri):
                return
            if os.path.exists(artifact.source_uri):
                self._load_content_from_file(artifact, artifact.source_uri)

    def _load_content_from_file(self, artifact: BaseArtifact, content_path: str) -> None:
        try:
            if isinstance(artifact, ImageArtifact):
                from PIL import Image
                artifact.set_content(Image.open(content_path))
            elif isinstance(artifact, AudioArtifact):
                with open(content_path, "rb") as f:
                    artifact.set_content(f.read())
            elif isinstance(artifact, TextArtifact):
                with open(content_path, "r", encoding=artifact.encoding) as f:
                    artifact.set_content(f.read())
            else:
                with open(content_path, "rb") as f:
                    artifact.set_content(f.read())
        except Exception as e:
            logger.error(f"Failed to load content from {content_path}: {e}")

    def delete(self, artifact_id: str) -> bool:
        try:
            metadata_path = self._find_metadata_file(artifact_id)
            if not metadata_path:
                return False

            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            if "_content_file" in metadata:
                content_path = os.path.join(os.path.dirname(metadata_path), metadata["_content_file"])
                if os.path.exists(content_path):
                    os.remove(content_path)
            os.remove(metadata_path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete artifact {artifact_id}: {e}")
            return False

    def exists(self, artifact_id: str) -> bool:
        return self._find_metadata_file(artifact_id) is not None

    def list_all(self, artifact_type: Optional[str] = None) -> List[dict]:
        try:
            artifacts = []
            subdirs = [artifact_type] if artifact_type else ["texts", "images", "audio", "prompts", "conversations"]

            for subdir in subdirs:
                dir_path = os.path.join(self.base_directory, subdir)
                if not os.path.exists(dir_path):
                    continue
                for filename in os.listdir(dir_path):
                    if not filename.endswith(".json"):
                        continue
                    try:
                        with open(os.path.join(dir_path, filename), "r", encoding="utf-8") as f:
                            artifacts.append(json.load(f))
                    except Exception as e:
                        logger.warning(f"Failed to read {filename}: {e}")

            artifacts.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            return artifacts
        except Exception as e:
            logger.error(f"Failed to list artifacts: {e}")
            return []
