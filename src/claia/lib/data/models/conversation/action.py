"""
Action data model for conversation audit trail.

Actions represent events that occur during a conversation's lifecycle,
providing a complete audit trail for debugging and analysis.
"""

# External dependencies
from typing import Dict, Any, Optional
import logging
import time
import uuid

# Internal dependencies
from ....enums.conversation import ActionType


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               ACTION                                 #
########################################################################
class Action:
    """
    Class representing an action in a conversation history.
    
    Actions provide an audit trail of all changes and events in a conversation,
    including message creation, updates, tool usage, and setting changes.
    """

    def __init__(self,
                 action_type: ActionType,
                 metadata: Optional[Dict[str, Any]] = None,
                 action_id: Optional[str] = None,
                 timestamp: Optional[float] = None):
        """
        Initialize an action.

        Args:
            action_type: The type of action
            metadata: Optional metadata for the action
            action_id: Optional ID for the action (generated if not provided)
            timestamp: Optional timestamp for the action
        """
        self.action_id = action_id or str(uuid.uuid4())
        self.action_type = action_type if isinstance(action_type, ActionType) else ActionType[action_type]
        self.metadata = metadata or {}
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the action to a dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.name,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Create an action from a dictionary."""
        return cls(
            action_type=data.get("action_type", ActionType.CREATE_CONVERSATION.name),
            metadata=data.get("metadata", {}),
            action_id=data.get("action_id"),
            timestamp=data.get("timestamp")
        )

