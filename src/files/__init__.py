"""
This package contains file handling functionality for CLAIA.
"""

from .base import BaseFile
from .manifest import FileManifest, MANIFEST_FILENAME
from .image import ImageFile
from .text import TextFile
from .prompt import Prompt
from .conversation import Conversation, Message, Action