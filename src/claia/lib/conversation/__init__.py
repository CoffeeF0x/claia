"""
Conversation package for CLAIA.

This package provides pure data models and repository interfaces for managing
conversations. Models are independent of persistence, and repositories provide
pluggable storage backends.

Main exports:
    Models:
        - Conversation: Main conversation model
        - Message: Individual message in a conversation
        - Action: Audit trail action
        - ToolDefinition: Tool/function definition
        - ConversationSettings: Conversation settings

    Repositories:
        - ConversationRepository: Abstract base repository
        - FileConversationRepository: File-based storage
        - MemoryRepository: In-memory storage
"""

# Export models
from .models import (
    Conversation,
    Message,
    Action,
    ToolDefinition,
    ConversationSettings,
)

# Export repositories
from .repositories import (
    ConversationRepository,
    FileConversationRepository,
    MemoryRepository,
)

__all__ = [
    # Models
    "Conversation",
    "Message",
    "Action",
    "ToolDefinition",
    "ConversationSettings",
    # Repositories
    "ConversationRepository",
    "FileConversationRepository",
    "MemoryRepository",
]

