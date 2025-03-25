# CLAIA File System

The CLAIA File System provides a comprehensive, modular approach to handling files within the application. It's designed to centralize file management, provide type-specific functionality, and simplify common file operations.

## Key Components

### FileManifest

The `FileManifest` is a singleton class that provides centralized tracking of all files in the system:

- Stores metadata about files
- Tracks file references
- Manages file status (active, deleted, etc.)
- Handles cleanup of old files

### BaseFile

The `BaseFile` class provides core file functionality:

- Directory management
- File saving and loading
- External file references
- Metadata storage and retrieval
- Reference tracking
- File export capabilities

### Specialized File Classes

Specialized classes extend `BaseFile` to provide type-specific functionality:

- `ImageFile`: For handling image files with operations like resizing, format conversion, and metadata extraction

## Basic Usage

### Creating and Saving Files

```python
# Create from a local file
file = BaseFile.from_path("/path/to/file.txt", base_directory="./files")
file.save()

# Create from a URL (as reference by default)
file = BaseFile.from_url("https://example.com/file.pdf", base_directory="./files")
file.save()
```

### Loading Files

```python
# Load a file by ID
file = BaseFile.load(file_id, base_directory="./files")
```

### Working with References

```python
# Add a reference to track what's using the file
file.add_reference("conversation_123")

# Remove a reference when it's no longer needed
file.remove_reference("conversation_123")
```

### Exporting Files

```python
# Export a file to an external location
success = file.export("/path/to/output.txt")

# Export with force overwrite if the target already exists
success = file.export("/path/to/existing_file.txt", force_overwrite=True)
```

### Managing File Lifecycle

```python
# Mark a file for deletion (will be cleaned up later)
file.mark_for_deletion()

# Clean up old deleted files
deleted_count = BaseFile.cleanup_deleted_files("./files", older_than_days=30)
```

## Working with Images

```python
# Create an image file
image = ImageFile.from_path("image.jpg", base_directory="./files")

# Extract metadata
metadata = image.process()
print(f"Image dimensions: {image.width}x{image.height}")

# Get base64 representation for embedding
base64_data = image.get_base64()

# Convert to a different format
png_image = image.convert("png")

# Resize the image
resized = image.resize(width=800, height=600, keep_aspect_ratio=True)

# Export the image to an external location
success = image.export("/path/to/output.jpg")
```

## External vs Internal Files

The file system supports two types of file storage:

1. **Internal files**: Files are copied to the application's storage directory
2. **External references**: Only metadata is stored; the file remains in its original location

```python
# Store a copy of the file in the system
file = BaseFile.from_path("/path/to/file.txt", base_directory="./files", is_reference=False)

# Store only a reference to the file
file = BaseFile.from_path("/path/to/file.txt", base_directory="./files", is_reference=True)
```

## Directory Structure

Files are organized into subdirectories based on their type:

- `text/`: Text files
- `images/`: Image files  
- `audio/`: Audio files
- `video/`: Video files
- `documents/`: Document files (PDF, Word, etc.)
- And more...

The system automatically determines the appropriate subdirectory based on the file's MIME type.

## Core Design Principles

1. **Centralized management**: All file metadata is tracked in one place
2. **Safe deletion**: Files are marked for deletion rather than immediately deleted
3. **Reference tracking**: Track which objects are using each file
4. **Type-specific functionality**: Specialized classes for different file types
5. **Consistent interface**: All file classes share a common interface 