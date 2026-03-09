"""
Domain events for CLAIA data models.

Domain events are lightweight notifications emitted by mutable objects
like Conversation. Runtime layers (CLI, API, workers) can consume these
events and decide if/how to persist state changes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import uuid


@dataclass
class DomainEvent:
    """Represents a single domain-level state change notification."""

    event_type: str
    entity_id: str
    entity_type: str
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the event to a JSON-safe dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
