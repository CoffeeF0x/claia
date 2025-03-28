# CLAIA File Manifest System

## Overview

The File Manifest system in CLAIA is a centralized registry for tracking and managing all files in the application. It serves as a metadata repository, providing a unified way to discover, query, and manage files across the system.

## Key Features

- **Centralized file tracking**: Single source of truth for file metadata
- **Efficient file lookup**: Fast lookup by file ID without traversing directories
- **Metadata storage**: Store and retrieve rich file metadata
- **File status tracking**: Track file lifecycle states
- **Reference tracking**: Track which objects reference a file
- **File discovery**: Find files by various criteria
- **Cleanup management**: Identify files ready for deletion

## File Manifest Structure

The file manifest is stored as a JSON file (`manifest.json`) at the root of the base directory:

```
base_directory/
├── text/
├── images/
├── ...
└── manifest.json
```

The manifest file contains a dictionary of file entries, keyed by the file ID:

```json
{
  "file_id_1": {
    "file_id": "file_id_1",
    "file_name": "example.txt",
    "path": "/path/to/text/file_id_1",
    "mime_type": "text/plain",
    "timestamp": 1615982400.0,
    "status": "active",
    "references": ["conversation_123", "message_456"],
    "metadata": {
      "encoding": "utf-8",
      "line_count": 42,
      "word_count": 256,
      "author": "CLAIA User"
    }
  },
  "file_id_2": {
    "file_id": "file_id_2",
    "file_name": "example.jpg",
    "path": "/path/to/images/file_id_2",
    "mime_type": "image/jpeg",
    "timestamp": 1615982500.0,
    "status": "active",
    "references": [],
    "metadata": {
      "width": 1024,
      "height": 768,
      "format": "JPEG"
    }
  }
}
```

## FileManifest Class API

### Initialization

```python
from files import FileManifest

# Initialize the manifest
manifest = FileManifest("/path/to/base_directory")
```

### Adding and Updating Files

```python
# Add or update a file in the manifest
manifest.add_or_update_file(
    file_id="file_id_1",
    file_name="example.txt",
    path="/path/to/text/file_id_1",
    mime_type="text/plain",
    timestamp=1615982400.0,
    status="active",
    metadata={
        "encoding": "utf-8",
        "line_count": 42,
        "word_count": 256
    }
)
```

### Getting File Metadata

```python
# Get metadata for a specific file
metadata = manifest.get_file_metadata("file_id_1")

# Check if a file exists in the manifest
exists = manifest.file_exists("file_id_1")
```

### Managing References

```python
# Add a reference to a file
manifest.add_reference("file_id_1", "conversation_123")

# Remove a reference from a file
manifest.remove_reference("file_id_1", "conversation_123")

# Get all files referenced by an object
files = manifest.get_files_by_reference("conversation_123")
```

### Finding Files

```python
# Get all files
all_files = manifest.get_all_files()

# Find files by status
deleted_files = manifest.find_files(status="deleted")

# Find files by type
image_files = manifest.find_files(file_type="image")

# Find files by metadata criteria
large_images = manifest.find_files(
    file_type="image",
    metadata_filters={
        "width": {"$gt": 1000},
        "height": {"$gt": 800}
    }
)

# Find files by timestamp range
recent_files = manifest.find_files(
    timestamp_range=(yesterday, today)
)
```

### Cleanup Management

```python
# Find files ready for cleanup
cleanup_files = manifest.cleanup_files(older_than_days=30)
```

### Saving and Loading

```python
# Save changes to the manifest file
manifest.save()

# Reload the manifest from disk
manifest.load()
```

## File Status Lifecycle

Files in the manifest have a status that indicates their current lifecycle state:

1. **ACTIVE**: Normal, active file
2. **EXTERNAL**: File exists at an external location (URL or path)
3. **DELETED**: Marked for deletion, but not yet physically removed
4. **MISSING**: File entry exists in manifest but the file is not found
5. **EMPTY**: File exists but has no content

## Metadata Filtering

The manifest supports sophisticated metadata filtering with MongoDB-like query operators:

```python
# Find files with specific metadata conditions
files = manifest.find_files(
    metadata_filters={
        "line_count": {"$gt": 100},          # greater than
        "word_count": {"$lte": 1000},        # less than or equal
        "tags": {"$in": ["important", "draft"]},  # in list
        "author": {"$eq": "CLAIA User"}      # equal to
    }
)
```

Supported operators:
- `$eq`: Equal to
- `$ne`: Not equal to
- `$gt`: Greater than
- `$gte`: Greater than or equal to
- `$lt`: Less than
- `$lte`: Less than or equal to
- `$in`: In a list of values
- `$nin`: Not in a list of values
- `$exists`: Field exists
- `$type`: Field is of a specific type
- `$regex`: Field matches a regular expression pattern

## Performance Considerations

- The manifest is loaded into memory when initialized, providing fast lookups
- For large manifests, consider:
  - Periodic cleanup of deleted files
  - Segmenting manifests by project or user
  - Using database backend for very large deployments

## Thread Safety

- The current implementation is not thread-safe
- For multi-threaded applications, ensure proper synchronization when accessing the manifest

## Integration with BaseFile

The `FileManifest` class is tightly integrated with the `BaseFile` class and its subclasses:

```python
# BaseFile automatically updates the manifest
file = BaseFile.from_source("/path/to/file.txt", base_directory)
file.save()  # Automatically updates the manifest

# TextFile also integrates with the manifest
text_file = TextFile.from_string("Content", base_directory)
text_file.save()  # Updates manifest with text statistics

# Conversation (extends TextFile) integrates with the manifest
conversation = Conversation.create_conversation(base_directory, "Title")
conversation.add_message("user", "Hello")  # Metadata updated in manifest

# Manifest changes affect file behavior
file.mark_for_deletion()  # Updates status in manifest
```

## Example Usage Patterns

### Creating and Tracking New Files

```python
# Create a new file
text_file = TextFile.from_string(
    content="Hello, World!",
    base_directory="/path/to/base_dir",
    file_name="greeting.txt"
)

# Access the manifest to verify
manifest = FileManifest("/path/to/base_dir")
metadata = manifest.get_file_metadata(text_file.file_id)
print(f"File status: {metadata['status']}")
```

### Tracking File References

```python
# Create a conversation that references a file
conversation = Conversation.create_conversation(
    base_directory="/path/to/base_dir",
    title="Document Discussion"
)

# Add a message with a file reference
conversation.add_message(
    role="user",
    content="Please review this document",
    file_ids=[text_file.file_id]  # References are tracked in the manifest
)

# Check file references
manifest = FileManifest("/path/to/base_dir")
references = manifest.get_file_metadata(text_file.file_id)["references"]
print(f"File is referenced by: {references}")
```

### Bulk File Operations

```python
# Find all files with a specific tag
manifest = FileManifest("/path/to/base_dir")
draft_files = manifest.find_files(
    metadata_filters={"tags": {"$in": ["draft"]}}
)

# Process these files
for file_id, metadata in draft_files.items():
    # Load the file
    file = BaseFile(base_directory="/path/to/base_dir", **metadata)

    # Perform operations
    print(f"Processing: {file.file_name}")

    # Update metadata
    file.metadata["processed"] = True
    file.save_metadata()
```

## Best Practices

1. **Always use the manifest for file discovery** rather than traversing directories

2. **Update the manifest when making file changes** outside the BaseFile API

3. **Add references** when files are used by other objects to track dependencies

4. **Periodically clean up** deleted files to maintain performance

5. **Use the file manifest as a query engine** for finding files by criteria

6. **Handle missing files gracefully** by checking file existence after retrieving from manifest