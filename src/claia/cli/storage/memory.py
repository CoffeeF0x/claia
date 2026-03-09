"""
In-memory storage for CLI artifacts.
"""

import logging
from typing import Optional, List, Dict

from .base import ArtifactStore
from claia.lib.data.models import BaseArtifact

logger = logging.getLogger(__name__)


class MemoryStore(ArtifactStore):
    """In-memory implementation of ArtifactStore."""

    def __init__(self):
        self._artifacts: Dict[str, BaseArtifact] = {}

    def save(self, artifact: BaseArtifact) -> bool:
        try:
            data = artifact.to_dict()
            artifact_type = type(artifact)
            artifact_copy = artifact_type.from_dict(data)
            if artifact.has_content_loaded():
                artifact_copy._content = artifact._content
                artifact_copy._content_loaded = True
            self._artifacts[artifact.id] = artifact_copy
            return True
        except Exception as e:
            logger.error(f"Failed to save artifact {artifact.id} in memory: {e}")
            return False

    def load(self, artifact_id: str, load_content: bool = False) -> Optional[BaseArtifact]:
        try:
            if artifact_id not in self._artifacts:
                return None
            stored = self._artifacts[artifact_id]
            data = stored.to_dict()
            artifact_type = type(stored)
            artifact_copy = artifact_type.from_dict(data)
            if load_content and stored.has_content_loaded():
                artifact_copy._content = stored._content
                artifact_copy._content_loaded = True
            return artifact_copy
        except Exception as e:
            logger.error(f"Failed to load artifact {artifact_id} from memory: {e}")
            return None

    def delete(self, artifact_id: str) -> bool:
        if artifact_id in self._artifacts:
            del self._artifacts[artifact_id]
            return True
        return False

    def exists(self, artifact_id: str) -> bool:
        return artifact_id in self._artifacts

    def list_all(self, artifact_type: Optional[str] = None) -> List[dict]:
        try:
            artifacts = []
            for artifact in self._artifacts.values():
                metadata = artifact.to_dict()
                if artifact_type and metadata.get("artifact_type") != artifact_type:
                    continue
                artifacts.append(metadata)
            artifacts.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            return artifacts
        except Exception as e:
            logger.error(f"Failed to list artifacts from memory: {e}")
            return []

    def clear(self) -> None:
        self._artifacts.clear()

    def count(self) -> int:
        return len(self._artifacts)
