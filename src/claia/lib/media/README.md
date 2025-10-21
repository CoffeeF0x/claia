## Media Package

Pure data models and repository interfaces for managing media files (text, images, audio, prompts).

## Overview

This package provides a clean separation between media file models and their persistence mechanisms, following the Repository Pattern. This architecture enables:

- **Flexibility**: Use any storage backend (files, databases, memory)
- **Lazy Loading**: Load metadata separately from content
- **Reference Support**: Reference external files without copying
- **Type Safety**: Specific models for different media types
- **Testability**: Easy testing with in-memory repositories

## Architecture

```
media/
├── models/              # Pure data models (no persistence logic)
│   ├── base_file.py     # Base file model
│   ├── text_file.py     # Text file model
│   ├── image_file.py    # Image file model (PIL Image support)
│   ├── audio_file.py    # Audio file model
│   └── prompt.py        # Prompt template model
├── repositories/        # Persistence layer
│   ├── base.py         # Abstract repository interface
│   ├── file_system_repository.py  # Disk storage
│   └── memory_repository.py  # In-memory storage
└── utils/              # Helper utilities (future)
```

## Quick Start

### Creating Files

```python
from claia.lib.media import TextFile, ImageFile, AudioFile, FileRepository

# From content
text = TextFile.from_content("Hello, world!", "greeting.txt")

# From path (import)
image = ImageFile.from_path("/path/to/photo.jpg", is_reference=False)

# From path (reference only, no copy)
doc = TextFile.from_path("/path/to/document.pdf", is_reference=True)

# From URL (reference)
audio = AudioFile.from_url("https://example.com/audio.mp3", is_reference=True)

# From URL (download)
audio2 = AudioFile.from_url("https://example.com/audio.mp3", is_reference=False)
```

### Using Repositories

#### File System Storage

```python
from claia.lib.media import FileRepository

# Initialize repository
file_repo = FileRepository.create_file_system("/data")

# Save file
text = TextFile.from_content("Analysis results", "results.txt")
file_repo.save(text)

# Load file (metadata only)
loaded = file_repo.load(text.id)
print(f"{loaded.file_name}: {loaded.size} bytes")

# Load file with content
loaded = file_repo.load(text.id, load_content=True)
print(loaded.content)  # Access the text content

# List all files
all_files = file_repo.list_all()
for metadata in all_files:
    print(f"{metadata['file_name']} ({metadata['size']} bytes)")

# List by type
images = file_repo.list_all(file_type='images')
```

#### In-Memory Storage (for testing)

```python
# Initialize in-memory repository
repo = FileRepository.create_memory()

# Same interface as file system repository
repo.save(text)
loaded = repo.load(text.id, load_content=True)

# Testing helpers
repo.clear()  # Clear all files
count = repo.count()  # Get count
```

### Storage Structure

File system repository uses this structure:

```
files/
├── texts/
│   ├── abc-123.json              # Small text (content inline in JSON)
│   ├── def-456.json              # Large text (metadata only)
│   └── def-456.txt               # Large text content
├── images/
│   ├── ghi-789.json              # Image metadata
│   └── ghi-789.jpg               # Image data
├── audio/
│   ├── jkl-012.json
│   └── jkl-012.mp3
└── prompts/
    └── mno-345.json              # Prompt (content inline)
```

**Strategy:**
- Small files (< 10KB): Content stored inline in JSON
- Large files: Separate content file + metadata JSON
- References: Only metadata stored, no content copied

### Integration with Conversations

```python
from claia.lib.conversation import Conversation
from claia.lib.media import TextFile, FileRepository
from claia.lib.enums.conversation import MessageRole

# Initialize repositories
file_repo = FileRepository.create_file_system("/data")
conv_repo = ConversationRepository.create_file_system("/data")

# Create and save files
text = TextFile.from_content("Analysis results", "results.txt")
image = ImageFile.from_path("/path/to/chart.png", is_reference=False)

file_repo.save(text)
file_repo.save(image)

# Create conversation
conversation = Conversation(title="Analysis Review")

# Add message with files
message = conversation.add_message(
    MessageRole.USER,
    "Please review these files",
    file_ids=[text.id, image.id]
)

# Later: Load files for the message (conversation convenience method!)
files = conversation.load_message_files(
    message.message_id,
    file_repo,
    load_content=True
)

# Process files
for file in files:
    if isinstance(file, ImageFile):
        # Process image
        img = file.content  # PIL Image object
        print(f"Image: {img.size}")
    elif isinstance(file, TextFile):
        # Process text
        print(f"Text: {file.content}")

# Attach/detach files
conversation.attach_file(message.message_id, another_file.id)
conversation.detach_file(message.message_id, text.id)

# Get all file IDs in conversation
all_file_ids = conversation.get_all_file_ids()

# Load all files for all messages
all_files = conversation.load_all_files(file_repo, load_content=False)
# Returns: {message_id: [files]}
```

### Factory Methods

Repository has factory methods for auto-detecting file types:

```python
# Auto-detect from path
file = file_repo.create_from_path("/path/to/file.jpg", is_reference=False)
# Returns: ImageFile

file = file_repo.create_from_path("/path/to/document.txt", is_reference=True)
# Returns: TextFile (as reference)

# Auto-detect from URL
file = file_repo.create_from_url("https://example.com/audio.mp3")
# Returns: AudioFile (as reference by default)
```

### Lazy Loading

Content is lazily loaded for performance:

```python
# Load metadata only (fast)
file = file_repo.load(file_id, load_content=False)
print(f"{file.file_name}: {file.size} bytes")  # Available
# file.content would be empty at this point

# Load content when needed
file = file_repo.load(file_id, load_content=True)
print(file.content)  # Content now loaded

# Or load later
file = file_repo.load(file_id)
# ... do other things ...
if need_content:
    content = file.load_content()  # Load on demand
```

### File Types

#### TextFile

```python
text = TextFile.from_content("Hello", "greeting.txt", encoding="utf-8")
print(text.content)  # String
print(text.encoding)  # utf-8
```

#### ImageFile

```python
from PIL import Image

# From PIL Image
img = Image.open("/path/to/image.jpg")
image_file = ImageFile.from_image(img, "photo.jpg")

# Load and access
loaded = file_repo.load(image_file.id, load_content=True)
pil_image = loaded.content  # PIL Image object
print(f"Dimensions: {loaded.width}x{loaded.height}")
print(f"Format: {loaded.format}")  # JPEG, PNG, etc.
```

#### AudioFile

```python
audio = AudioFile.from_path("/path/to/audio.mp3", is_reference=False)
print(f"Duration: {audio.duration}s")
print(f"Format: {audio.format}")  # MP3, WAV, etc.

# Access binary data
loaded = file_repo.load(audio.id, load_content=True)
audio_bytes = loaded.content  # bytes
```

#### Prompt

```python
from claia.lib.media import Prompt

# Create prompt (validates name formatting)
prompt = Prompt.from_content(
    "You are a helpful assistant",
    prompt_name="helpful assistant",  # Converts to: helpful-assistant
    prompt_type="system"
)

file_repo.save(prompt)

# Prompt names are validated: lowercase, hyphens only
print(prompt.prompt_name)  # "helpful-assistant"
```

### Reference vs Import

```python
# Reference (no copy, just stores path/URL)
ref = TextFile.from_path("/etc/hosts", is_reference=True)
file_repo.save(ref)  # Only saves metadata
print(ref.source_path)  # /etc/hosts
print(ref.is_reference)  # True

# Import (copies content into repository)
imported = TextFile.from_path("/etc/hosts", is_reference=False)
file_repo.save(imported)  # Copies content
print(imported.is_reference)  # False

# URL reference (common for external resources)
url_ref = ImageFile.from_url("https://example.com/logo.png", is_reference=True)
file_repo.save(url_ref)  # Only saves metadata + URL

# URL download (downloads and stores)
downloaded = ImageFile.from_url("https://example.com/logo.png", is_reference=False)
file_repo.save(downloaded)  # Downloads and stores content
```

## Design Principles

1. **Foundation Layer**: Media package knows nothing about conversations
2. **Pure Models**: Files are simple data objects
3. **Lazy Loading**: Content loaded only when needed
4. **Generic Operations**: Conversation methods work with any file type
5. **No Circular Dependencies**: Clean dependency flow

## Dependency Flow

```
media (foundation)
  ↓
conversation (advanced, can use media)
  ↓
CLI/applications (can use both)
```

## Best Practices

1. **Lazy Load**: Don't load content unless you need it
2. **Use Repositories**: Always persist through repositories
3. **Reference Large Files**: Use `is_reference=True` for large external files
4. **Factory Methods**: Use `create_from_path/url` for auto-detection
5. **Type Check**: Use `isinstance()` to handle specific file types

## Examples

### Multi-Modal Conversation

```python
# Create various file types
text = TextFile.from_content("Describe this image", "query.txt")
image = ImageFile.from_path("/path/to/photo.jpg", is_reference=False)
audio = AudioFile.from_url("https://example.com/audio.mp3", is_reference=True)

# Save all files
for file in [text, image, audio]:
    file_repo.save(file)

# Create conversation with all file types
conversation = Conversation(title="Multi-modal Analysis")
message = conversation.add_message(
    MessageRole.USER,
    "Analyze these",
    file_ids=[text.id, image.id, audio.id]
)

# Process based on type
files = conversation.load_message_files(message.message_id, file_repo, load_content=True)

for file in files:
    if isinstance(file, TextFile):
        print(f"Text: {file.content}")
    elif isinstance(file, ImageFile):
        print(f"Image: {file.dimensions}")
    elif isinstance(file, AudioFile):
        print(f"Audio: {file.duration}s")
```

### Batch File Operations

```python
# Load multiple files efficiently
file_ids = ["id1", "id2", "id3"]
files = file_repo.load_multiple(file_ids, load_content=False)

# Process metadata only (fast)
for file in files:
    print(f"{file.file_name}: {file.size} bytes")

# Then load content for specific files
for file in files:
    if file.size < 1024 * 1024:  # < 1MB
        file.load_content()
        # Process content...
```

## Migration from Old Structure

Old code using the file-based classes can be gradually migrated:

```python
# Old way (tightly coupled to files)
from claia.lib.files import TextFile
text = TextFile(base_directory="/data", file_name="test.txt")
text.save("Hello")

# New way (pure models + repositories)
from claia.lib.media import TextFile, FileRepository
text = TextFile.from_content("Hello", "test.txt")
repo = FileRepository.create_file_system("/data")
repo.save(text)
```

## Testing

Use memory repository for fast, isolated tests:

```python
import pytest
from claia.lib.media import FileRepository, TextFile

@pytest.fixture
def file_repo():
    return FileRepository.create_memory()

def test_file_creation(file_repo):
    text = TextFile.from_content("Test", "test.txt")
    file_repo.save(text)
    
    loaded = file_repo.load(text.id, load_content=True)
    assert loaded.content == "Test"
```

## See Also

- `conversation/README.md` - Conversation models and repositories
- `conversation/models/conversation.py` - File convenience methods

