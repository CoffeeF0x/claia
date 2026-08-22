"""
Domain events for CLAIA data models.

Domain events represent state changes within mutable objects like Conversation.
They serve a dual purpose:
  1. Audit trail — persisted as part of the conversation's serialized state.
  2. Runtime notifications — listeners (CLI, API, workers) react to events
     to trigger persistence, sync, or side effects.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import uuid

from ..enums.events import EventType


@dataclass
class DomainEvent:
    """A single domain-level state change — stored and emitted."""

    event_type: EventType
    entity_id: str
    entity_type: str = "conversation"
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        raw_type = data.get("event_type", "CONVERSATION_CREATED")
        event_type = EventType[raw_type]

        return cls(
            event_type=event_type,
            entity_id=data.get("entity_id", ""),
            entity_type=data.get("entity_type", "conversation"),
            timestamp=data.get("timestamp", time.time()),
            event_id=data.get("event_id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata", {}),
        )
