"""
Tool definition data model for conversations.

ToolDefinitions describe tools/functions that can be called during a conversation,
including their parameters and return types.
"""

# External dependencies
from typing import Dict, Any, Optional
import logging
import uuid
import time


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                           TOOL DEFINITION                            #
########################################################################
class ToolDefinition:
    """
    Class representing a tool definition in a conversation.
    
    Tool definitions describe callable functions/tools that can be invoked
    during conversation processing, including their parameters and return schemas.
    """

    def __init__(self,
                 name: str,
                 description: str,
                 parameters: Dict[str, Any],
                 returns: Dict[str, Any] = None,
                 tool_id: Optional[str] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None):
        """
        Initialize a tool definition.

        Args:
            name: The name of the tool
            description: The description of the tool
            parameters: The parameters of the tool
            returns: The return value schema of the tool (default: {"type": "string"})
            tool_id: Optional ID for the tool (generated if not provided)
            created_at: Optional timestamp for creation time
            updated_at: Optional timestamp for last update time
        """
        self.tool_id = tool_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.parameters = parameters
        self.returns = returns or {"type": "string"}
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert the tool definition to a dictionary."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "returns": self.returns,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolDefinition':
        """Create a tool definition from a dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            returns=data.get("returns", {"type": "string"}),
            tool_id=data.get("tool_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

