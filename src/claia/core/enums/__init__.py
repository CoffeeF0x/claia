"""
Domain enums for claia.core.

These enums describe roles, statuses, and capability flags used across
the data models and runtime.
"""

from .conversation import MessageRole
from .file import FileSubdirectory, FileStatus, FileMimeType
from .logging import LogLevel, LogFormat
from .model import ModelCapability, IOType, SourcePreference
from .process import ProcessStatus
from .process_queue import ProcessQueueHook

__all__ = [
    "MessageRole",
    "FileSubdirectory", "FileStatus", "FileMimeType",
    "LogLevel", "LogFormat",
    "ModelCapability", "IOType", "SourcePreference",
    "ProcessStatus",
    "ProcessQueueHook",
]
