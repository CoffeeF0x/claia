# CLAIA Files Module - Class Hierarchy

## Overview

The CLAIA Files module is built on a carefully designed class hierarchy that allows for both common functionality and type-specific specialization. The design follows object-oriented principles with a base class providing foundational functionality and subclasses extending it with specialized features.

## Class Hierarchy

```
BaseFile
├── TextFile
│   ├── Prompt
│   └── Conversation
│       ├── Message (inner class)
│       └── Action  (inner class)
└── ImageFile
```

## BaseFile

The `BaseFile` class is the foundation of the file system, providing core functionality for all file types:

- File identification (ID, name)
- Storage path management
- File metadata handling
- Reference tracking
- File operations (save, load, export)
- File lifecycle management
- External URL handling

### Key Responsibilities

- **Storage Management**: Directory creation, path resolution
- **File Operations**: Reading, writing, copying, exporting files
- **Metadata Management**: Storing and retrieving file metadata
- **Reference Tracking**: Managing which objects reference a file
- **Lifecycle Management**: Tracking file status, deletion

### Key Methods

- `from_source()`: Create a file from an existing file or URL
- `from_content()`: Create a file from in-memory content
- `save()`: Save file content to storage
- `load()`: Load file metadata from storage
- `export()`: Export a file to an external location
- `exists()`: Check if the file exists

## TextFile

The `TextFile` class extends `BaseFile` to add specialized functionality for text-based files:

### Key Features

- Text encoding detection and handling
- Text statistics (line count, word count, character count)
- Content search and extraction
- Content preview generation

### Key Methods

- `from_string()`: Create a TextFile from a string
- `get_stats()`: Get text file statistics
- `search()`: Search for patterns in the text
- `get_preview()`: Get a preview of the text content
- `get_lines()`: Extract specific lines from the content

## ImageFile

The `ImageFile` class extends `BaseFile` to add specialized functionality for image files:

### Key Features

- Image dimensions and format detection
- Thumbnail generation
- Image format conversion
- Image metadata extraction (EXIF)

### Key Methods

- `get_dimensions()`: Get image width and height
- `generate_thumbnail()`: Create a smaller version of the image
- `convert_format()`: Convert the image to a different format
- `get_exif_data()`: Extract EXIF metadata from the image

## Prompt

The `Prompt` class extends `TextFile` to add specialized functionality for AI prompt templates:

### Key Features

- Template variable detection and management
- Template formatting with variable substitution
- Prompt versioning and history tracking
- Validation of prompt variables

### Key Methods

- `get_variables()`: Extract template variables from the prompt
- `format()`: Format the prompt by substituting variables
- `validate()`: Validate that all required variables are provided
- `get_history()`: Get prompt revision history

## Conversation

The `Conversation` class extends `TextFile` to manage chat conversations:

### Inner Classes

- `Message`: Represents a single message in the conversation
- `ToolDefinition`: Represents a tool definition in the conversation
- `Action`: Represents a user or system action in the conversation

### Key Features

- Message tracking and organization
- Support for different message roles (user, assistant, system)
- Message metadata and timestamps
- Tool definition management for AI assistants
- Action tracking (e.g., file uploads, regenerations)
- Conversation export in various formats
- Inherits text file functionality for content operations

### Key Methods

- `add_message()`: Add a new message to the conversation
- `add_action()`: Record an action in the conversation
- `get_messages()`: Retrieve all messages in the conversation
- `add_tool_definition()`: Add a tool definition to the conversation
- `apply_substitutions()`: Apply variable substitutions to text
- `export_as_markdown()`: Export the conversation as a Markdown document
- `export_as_json()`: Export the conversation as a JSON document

## FileManifest

The `FileManifest` class is a utility class (not in the inheritance hierarchy) that manages the file tracking system:

### Key Features

- Maintains a registry of all files in the system
- Tracks file metadata in a central location
- Provides search and filtering capabilities

### Key Methods

- `get_file_metadata()`: Get metadata for a specific file
- `get_all_files()`: Get a list of all files in the system
- `find_files()`: Find files by various criteria
- `cleanup_files()`: Find files that are ready for cleanup

## Class Interaction Patterns

### Creation Pattern

```
┌─────────┐     ┌───────────┐     ┌──────────────┐
│ Client  │────▶│ BaseFile  │────▶│ FileManifest │
└─────────┘     └───────────┘     └──────────────┘
                     │
                     ▼
                ┌─────────┐
                │ Storage │
                └─────────┘
```

### Loading Pattern

```
┌─────────┐     ┌──────────────┐      ┌───────────┐
│ Client  │────▶│ FileManifest │────▶│ BaseFile  │
└─────────┘     └──────────────┘      └───────────┘
                                            │
                                            ▼
                                       ┌─────────┐
                                       │ Storage │
                                       └─────────┘
```

### Reference Management Pattern

```
┌──────────────┐     ┌───────────┐      ┌──────────────┐
│ Conversation │────▶│ TextFile  │────▶│ FileManifest │
└──────────────┘     └───────────┘      └──────────────┘
                          │
                          ▼
                     ┌──────────┐
                     │ BaseFile │
                     └──────────┘
```

## Design Patterns Used

### Factory Method Pattern

The static `from_source()`, `from_content()`, and `from_string()` methods act as factory methods for creating file objects.

### Template Method Pattern

The `save()` method in `BaseFile` defines the template for saving files, with specialized behavior in subclasses through the `_post_save_hook()` method.

### Repository Pattern

The `FileManifest` class implements a repository pattern for file metadata storage and retrieval.

### Strategy Pattern

File type determination and subdirectory selection use a strategy pattern through the `FileSubdirectory` enum.

## Extension Points

The file system is designed to be extensible:

1. **New File Types**: Create a new subclass of `BaseFile` with specialized functionality

2. **Custom Storage Backends**: Extend `BaseFile` with methods to support different storage systems

3. **Additional Metadata**: Add custom metadata fields to file objects

4. **Custom Export Formats**: Add methods for exporting files in specialized formats