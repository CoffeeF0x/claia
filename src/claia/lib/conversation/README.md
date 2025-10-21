# Conversation Package

Pure data models and repository interfaces for managing conversations in CLAIA.

## Overview

This package provides a clean separation between conversation data models and their persistence mechanisms, following the Repository Pattern. This architecture enables:

- **Flexibility**: Use any storage backend (files, databases, memory)
- **Testability**: Easy testing with in-memory repositories
- **Thread Safety**: Concurrent streaming and tool processing
- **Database Ready**: Pure models can be mapped to any ORM
- **Audit Trail**: Complete action history for debugging

## Architecture

```
conversation/
├── models/              # Pure data models (no persistence logic)
│   ├── conversation.py  # Main conversation model
│   ├── message.py       # Message model with thread-safe operations
│   ├── action.py        # Action/event for audit trail
│   ├── tool_definition.py
│   └── conversation_settings.py
├── repositories/        # Persistence layer
│   ├── base.py         # Abstract repository interface
│   ├── file_repository.py  # JSON file storage
│   └── memory_repository.py  # In-memory storage
└── utils/              # Helper utilities
    └── tool_text.py    # Tool call text processing
```

## Quick Start

### Creating a Conversation

```python
from claia.lib.conversation import Conversation
from claia.lib.enums.conversation import MessageRole

# Create a new conversation (pure data model)
conversation = Conversation(title="My Conversation")

# Add messages
conversation.add_message(MessageRole.USER, "Hello!")
conversation.add_message(MessageRole.ASSISTANT, "Hi there!")

# Add tool definitions
conversation.add_tool_definition(
    name="get_weather",
    description="Get the current weather",
    parameters={"location": {"type": "string"}}
)
```

### Using Repositories

#### File-Based Storage

```python
from claia.lib.conversation import FileConversationRepository

# Initialize repository with a base directory
repo = FileConversationRepository("/path/to/conversations")

# Save conversation
repo.save(conversation)

# Load conversation
loaded = repo.load(conversation.id)

# List all conversations
all_convs = repo.list_all()

# Find by criteria
recent = repo.find_by_criteria(
    title="weather",
    created_after=1234567890,
    has_tools=True
)
```

#### In-Memory Storage (for testing)

```python
from claia.lib.conversation import MemoryRepository

# Initialize in-memory repository
repo = MemoryRepository()

# Same interface as file repository
repo.save(conversation)
loaded = repo.load(conversation.id)

# Additional testing helpers
repo.clear()  # Clear all conversations
count = repo.count()  # Get count
```

### Thread-Safe Message Operations

When streaming content and processing tools concurrently, use thread-safe message methods:

```python
# Get a message
message = conversation.get_latest_message()

# Thread-safe append (for streaming)
message.safe_append_content("streaming chunk")

# Thread-safe replace (for tool processing)
message.safe_replace_substring(
    start=10,
    end=20,
    replacement="[TOOL_RESULT]"
)

# Thread-safe read
content = message.safe_get_content()
```

### Streaming Support

The conversation has built-in streaming support:

```python
# Start streaming (creates START_STREAM action)
conversation.stream_message(
    message_id=msg.message_id,
    content="chunk",
    append=True
)

# End streaming (creates END_STREAM action)
conversation.stream_message(
    message_id=msg.message_id,
    content="",
    append=True,
    end=True
)
```

## Custom Repository Implementation

To create a custom repository (e.g., for a database):

```python
from claia.lib.conversation import ConversationRepository, Conversation
from typing import Optional, List, Dict, Any

class DatabaseRepository(ConversationRepository):
    def __init__(self, db_connection):
        self.db = db_connection
    
    def save(self, conversation: Conversation) -> bool:
        # Serialize and save to database
        data = conversation.to_dict()
        # ... your database logic
        return True
    
    def load(self, conversation_id: str) -> Optional[Conversation]:
        # Load from database and deserialize
        data = # ... fetch from database
        return Conversation.from_dict(data) if data else None
    
    def delete(self, conversation_id: str) -> bool:
        # ... your delete logic
        pass
    
    def list_all(self) -> List[Dict[str, Any]]:
        # ... your list logic
        pass
    
    def find_by_criteria(self, **filters) -> List[Conversation]:
        # ... your search logic
        pass
    
    def exists(self, conversation_id: str) -> bool:
        # ... your exists check
        pass
```

## Audit Trail

Every action in a conversation is tracked:

```python
# Actions are automatically created for all operations
conversation.add_message(...)  # Creates CREATE_MESSAGE action
conversation.update_message(...)  # Creates UPDATE_MESSAGE action
conversation.delete_message(...)  # Creates DELETE_MESSAGE action
conversation.change_title(...)  # Creates CHANGE_TITLE action
# ... and many more

# Access the audit trail
for action in conversation.actions:
    print(f"{action.action_type.name} at {action.timestamp}")
    print(f"  Metadata: {action.metadata}")
```

## Migration from Old Structure

The conversation models have been refactored from file-based classes to pure data models. Key changes:

### Removed Fields
- `tool_pattern_name` - Now handled by registry extensions
- `tool_protocol_name` - Now handled by registry extensions
- `custom_tag_formats` - Tag parsing moved to extensions
- `find_tags()` method - Use registry for tool detection

### Changed Fields
- `file_id` → `id` - Conversations now use `id` as primary identifier
- No longer inherits from `TextFile` or `BaseFile`

### New Features
- Thread-safe message operations
- Repository-based persistence
- Cleaner separation of concerns

### Backward Compatibility

Old conversation files can be loaded with FileRepository:

```python
repo = FileConversationRepository("/old/conversations")
# The repository can read the old JSON format
old_conv = repo.load("conversation-id")
```

## Tool Call Processing

Tool call text manipulation has been moved to utilities:

```python
from claia.lib.conversation.utils import find_tool_calls, validate_tool_call_json

# Find tool calls in text
calls = find_tool_calls(
    content=message.content,
    start_token="[TOOL_CALL]",
    end_token="[/TOOL_CALL]"
)

# Validate tool call JSON
is_valid = validate_tool_call_json('{"name": "test", "parameters": {}}')
```

## Best Practices

1. **Use Repositories**: Always persist conversations through repositories, not by calling internal methods
2. **Thread Safety**: Use `safe_*` methods when concurrent access is possible
3. **Audit Trail**: The action log is your friend for debugging - don't disable it
4. **Immutability**: Repositories return copies to prevent accidental mutations
5. **Testing**: Use `MemoryRepository` for fast, isolated tests

## Examples

See the tests in `src/tests/` for comprehensive examples of using conversations and repositories.

