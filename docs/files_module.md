# CLAIA Files Module Documentation

## Overview

The CLAIA Files module provides a comprehensive file management system for handling various file types within the CLAIA application. It features a modular, object-oriented design with a base class that handles common file operations, and specialized subclasses for specific file types like text, images, prompts, and conversations.

## Core Features

- **Unified file management interface** for various file types
- **Automatic file organization** with subdirectories based on file types
- **File metadata tracking** including timestamps, references, and custom metadata
- **Support for both local files and external references** (URLs)
- **File manifest system** for tracking all files in the system
- **Specialized file handlers** for different file types
- **File lifecycle management** including soft deletion and cleanup

## Module Structure

```
files/
├── __init__.py         # Package exports and initialization
├── base.py             # BaseFile class - core file operations
├── manifest.py         # FileManifest class - file tracking system
├── text.py             # TextFile class - text file operations
├── image.py            # ImageFile class - image file operations
├── prompt.py           # Prompt class - AI prompt management
└── conversation.py     # Conversation class - Chat conversation management
```

## Class Hierarchy

```
BaseFile
├── TextFile
│   ├── Prompt
│   └── Conversation
└── ImageFile
```

## Installation and Dependencies

The files module requires:

- Python 3.6+
- Core dependencies:
  - `uuid`, `mimetypes` (standard library)
  - `chardet` (for text encoding detection)
  - External dependencies depending on file type handlers (e.g., PIL for images)

## Basic Usage

### Common Import Pattern

```python
# Import the file types you need
from files import BaseFile, TextFile, ImageFile, Prompt, Conversation, FileManifest
```

### File Storage Structure

All files are organized into subdirectories based on their type:

```
base_directory/
├── text/            # Text files
├── images/          # Image files
├── prompts/         # AI prompts
├── conversations/   # Conversation records
└── manifest.json    # File manifest tracking all files
```

## Working with Files

### Creating Files

Files can be created from:

1. Existing local files:

```python
# Create a file from a local file path
file = BaseFile.from_source(
    source="/path/to/file.txt",
    base_directory="/storage/path"
)
```

2. External URLs:

```python
# Create a file reference to a URL
file = BaseFile.from_source(
    source="https://example.com/image.jpg",
    base_directory="/storage/path",
    is_reference=True  # Store only a reference to the URL
)

# Create a file by downloading from a URL
file = BaseFile.from_source(
    source="https://example.com/image.jpg",
    base_directory="/storage/path",
    is_reference=False  # Download the file content
)
```

3. In-memory content:

```python
# Create a file from a text string
text_file = TextFile.from_string(
    content="Hello, CLAIA!",
    base_directory="/storage/path",
    file_name="greeting.txt"
)
```

### Loading Files

```python
# Load a file by its ID (without content)
file_metadata = BaseFile.load(
    file_id="file_uuid",
    base_directory="/storage/path"
)

# Create a file object from metadata
file = BaseFile(
    base_directory="/storage/path",
    **file_metadata
)

# Get the file content
content = file.get_content()
```

### File Operations

```python
# Check if a file exists
if file.exists():
    # Get file size
    size = file.get_file_size()

    # Export the file to an external location
    file.export("/export/path/file.txt")

    # Mark file for deletion (soft delete)
    file.mark_for_deletion()
```

### Reference Management

```python
# Add a reference to the file (e.g., when used in a conversation)
file.add_reference("conversation_123")

# Remove a reference
file.remove_reference("conversation_123")
```

### Cleanup

```python
# Clean up deleted files that are older than 30 days
deleted_count = BaseFile.cleanup_deleted_files(
    base_directory="/storage/path",
    older_than_days=30
)
```

## File Manifest

The `FileManifest` class maintains a record of all files in the system:

```python
# Get the manifest
manifest = FileManifest("/storage/path")

# Get metadata for a specific file
metadata = manifest.get_file_metadata("file_uuid")

# Get all files
all_files = manifest.get_all_files()

# Find files by criteria
image_files = manifest.find_files(file_type="image")
```

## Specialized File Types

### Text Files

The `TextFile` class provides specialized functionality for text files:

```python
# Create a text file
text_file = TextFile.from_string(
    content="Hello, CLAIA!",
    base_directory="/storage/path",
    file_name="greeting.txt"
)

# Get text statistics
stats = text_file.get_stats()
print(f"Lines: {stats['line_count']}, Words: {stats['word_count']}")

# Search the content
results = text_file.search("CLAIA", case_sensitive=True)

# Get a preview
preview = text_file.get_preview(max_lines=5)

# Get specific lines
lines = text_file.get_lines(start=10, end=20)
```

### Image Files

The `ImageFile` class provides specialized functionality for image files:

```python
# Create an image file
image_file = ImageFile.from_source(
    source="/path/to/image.jpg",
    base_directory="/storage/path"
)

# Get image information
dimensions = image_file.get_dimensions()
print(f"Width: {dimensions['width']}, Height: {dimensions['height']}")

# Generate thumbnail
thumbnail_path = image_file.generate_thumbnail(width=200, height=200)

# Convert image format
png_path = image_file.convert_format("PNG")
```

### Prompts

The `Prompt` class manages AI prompt templates:

```python
# Create a prompt template
prompt = Prompt.from_string(
    content="Generate a {{style}} description of {{subject}}.",
    base_directory="/storage/path",
    name="description_generator"
)

# Format the prompt with variables
formatted = prompt.format(
    style="detailed",
    subject="CLAIA's file system"
)

# Get prompt variables
variables = prompt.get_variables()  # Returns ["style", "subject"]
```

### Conversations

The `Conversation` class manages chat conversations:

```python
# Create a new conversation
conversation = Conversation.create_conversation(
    base_directory="/storage/path",
    title="File System Discussion"
)

# Add a user message
conversation.add_message(
    role="user",
    content="How do I create a new file?"
)

# Add a message with a file reference
conversation.add_message(
    role="user",
    content="Here's an example image",
    file_ids=["file_uuid_1", "file_uuid_2"]
)

# Attach a file to an existing message
message = conversation.get_messages()[0]
conversation.attach_file(message.message_id, "file_uuid_3")

# Get all messages
messages = conversation.get_messages()

# Export the conversation
conversation.export_as_markdown("/export/path/conversation.md")

# Add a tool definition to the conversation
weather_tool = conversation.add_tool_definition(
    name="get_weather",
    description="Get the current weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or zip code"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
        },
        "required": ["location"]
    }
)

# Format prompt with tool definitions
formatted_prompt = conversation.apply_substitutions("""You have access to the following tools:
{tool_definitions}

If you need to call a tool, use the following format:
{tool_format}""")
```

## Advanced Usage

### Converting External References to Local Files

```python
# Create a reference to an external URL
file = BaseFile.from_source(
    source="https://example.com/image.jpg",
    base_directory="/storage/path",
    is_reference=True
)

# Later, download and store the file locally
file.convert_to_local()
```

### Finding Files by Criteria

```python
# Find all image files with a specific tag in metadata
images = BaseFile.find_files_by_criteria(
    base_directory="/storage/path",
    subdirectory="images",
    metadata_filters={"tags": "landscape"}
)
```

### Custom Metadata

```python
# Add custom metadata
file.metadata["author"] = "CLAIA User"
file.metadata["tags"] = ["important", "reference"]

# Save metadata
file.save_metadata()
```

## Best Practices

1. **Always use the base_directory parameter consistently** across your application to ensure proper file management.

2. **Use the appropriate specialized file class** for the file type you're working with.

3. **Add references** when files are used in other parts of your application to track dependencies.

4. **Regularly clean up deleted files** to manage storage.

5. **Check file existence** before performing operations on files.

6. **Handle URLs properly** by deciding whether to store as a reference or download content based on your use case.

## Error Handling

Most methods return `None`, `False`, or raise exceptions when operations fail. Always check return values and implement appropriate error handling:

```python
# Example error handling
file = BaseFile.from_source(source_path, base_directory)
if file is None:
    print("Failed to create file")
    # Handle the error

saved_path = file.save()
if saved_path is None:
    print("Failed to save file")
    # Handle the error
```

## Complete Example

```python
import os
from files import BaseFile, TextFile, ImageFile, FileManifest

# Setup storage location
base_dir = "/path/to/storage"

# Create a text file from content
text_file = TextFile.from_string(
    content="This is a sample document for the CLAIA file system.",
    base_directory=base_dir,
    file_name="sample.txt"
)

# Add some metadata
text_file.metadata["author"] = "CLAIA User"
text_file.metadata["category"] = "documentation"
text_file.save_metadata()

# Print some info about the file
print(f"File ID: {text_file.file_id}")
print(f"File Path: {text_file.path}")
print(f"File Size: {text_file.get_file_size()} bytes")

stats = text_file.get_stats()
print(f"Lines: {stats['line_count']}, Words: {stats['word_count']}")

# Create an image file from a URL
image_file = ImageFile.from_source(
    source="https://example.com/image.jpg",
    base_directory=base_dir,
    is_reference=False  # Download it
)

# Export the files to another location
export_dir = "/path/to/exports"
os.makedirs(export_dir, exist_ok=True)

text_file.export(os.path.join(export_dir, "exported_text.txt"))
image_file.export(os.path.join(export_dir, "exported_image.jpg"))

# Get the manifest to see all files
manifest = FileManifest(base_dir)
all_files = manifest.get_all_files()
print(f"Total files in system: {len(all_files)}")

# Clean up - mark files for deletion and then clean up
text_file.mark_for_deletion()
image_file.mark_for_deletion()

# This would normally be run after some time
# Here we use 0 days for demonstration
deleted_count = BaseFile.cleanup_deleted_files(base_dir, older_than_days=0)
print(f"Cleaned up {deleted_count} files")