"""
CLI storage abstractions.

These interfaces and implementations are owned by the CLI runtime.
CLAIA core models remain persistence-agnostic.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from claia.lib.data.models import BaseArtifact


class ArtifactStore(ABC):
    """Abstract storage interface for CLI-managed artifacts."""

    @abstractmethod
    def save(self, artifact: BaseArtifact) -> bool:
        pass

    @abstractmethod
    def load(self, artifact_id: str, load_content: bool = False) -> Optional[BaseArtifact]:
        pass

    @abstractmethod
    def delete(self, artifact_id: str) -> bool:
        pass

    @abstractmethod
    def exists(self, artifact_id: str) -> bool:
        pass

    def load_multiple(self, artifact_ids: List[str], load_content: bool = False) -> List[BaseArtifact]:
        artifacts = []
        for artifact_id in artifact_ids:
            artifact = self.load(artifact_id, load_content=load_content)
            if artifact:
                artifacts.append(artifact)
        return artifacts

    @abstractmethod
    def list_all(
        self,
        file_type: Optional[str] = None,
        artifact_type: Optional[str] = None,
    ) -> List[dict]:
        pass
