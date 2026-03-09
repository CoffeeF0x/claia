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
          │   ├── {id}.json
          ├── images/
          │   ├── {id}.json
          │   └── {id}.png
          ├── audio/
          │   ├── {id}.json
          │   └── {id}.mp3
          ├── prompts/
          │   └── {id}.json
          └── conversations/
              └── {id}.json
    """

    INLINE_THRESHOLD = 10 * 1024

    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        os.makedirs(self.base_directory, exist_ok=True)

    def _get_type_directory(self, artifact: BaseArtifact) -> str:
        type_dirs = {
            "text": os.path.join(self.base_directory, "texts"),
            "images": os.path.join(self.base_directory, "images"),
            "audio": os.path.join(self.base_directory, "audio"),
            "prompts": os.path.join(self.base_directory, "prompts"),
            "conversations": os.path.join(self.base_directory, "conversations"),
        }

        artifact_type = artifact.get_file_type().value
        dir_path = type_dirs.get(artifact_type, os.path.join(self.base_directory, artifact_type))
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def _get_metadata_path(self, artifact: BaseArtifact) -> str:
        type_dir = self._get_type_directory(artifact)
        return os.path.join(type_dir, f"{artifact.id}.json")

    def _get_content_path(self, artifact: BaseArtifact) -> str:
        type_dir = self._get_type_directory(artifact)
        ext = os.path.splitext(artifact.file_name)[1]
        if not ext:
            if artifact.mime_type.startswith("image/"):
                ext = ".jpg"
            elif artifact.mime_type.startswith("audio/"):
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

            if artifact.has_content_loaded():
                if self._should_inline_content(artifact):
                    metadata["_inline_content"] = artifact._content
                else:
                    content_path = self._get_content_path(artifact)
                    self._save_content_file(artifact, content_path)
                    metadata["_content_file"] = os.path.basename(content_path)

            if artifact.is_reference and artifact.source_path:
                metadata["_reference_source"] = artifact.source_path

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
        file_type = metadata.get("file_type", "texts")
        if file_type == "conversations":
            return Conversation.from_dict(metadata)
        if file_type == "prompts" or metadata.get("prompt_name"):
            return Prompt.from_dict(metadata)
        if file_type == "images":
            return ImageArtifact.from_dict(metadata)
        if file_type == "audio":
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
        if artifact.is_reference and artifact.source_path:
            if artifact.is_url(artifact.source_path):
                return
            if os.path.exists(artifact.source_path):
                self._load_content_from_file(artifact, artifact.source_path)

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

    def list_all(
        self,
        file_type: Optional[str] = None,
        artifact_type: Optional[str] = None,
    ) -> List[dict]:
        try:
            artifacts = []
            # Accept both naming styles; file_type takes precedence.
            type_filter = file_type if file_type is not None else artifact_type
            subdirs = [type_filter] if type_filter else ["texts", "images", "audio", "prompts", "conversations"]

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
