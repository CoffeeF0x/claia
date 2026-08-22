"""
Domain enums for claia.core.

These enums describe roles, statuses, and capability flags used across
the data models and runtime.
"""

from .conversation import MessageRole
from .file import FileSubdirectory, FileStatus, FileMimeType
from .logging import LogLevel, LogFormat
from .model import ModelCapability, IOType, SourcePreference
from .task import TaskStatus, TaskEvent
from .task_queue import TaskQueueHook
from .data import (
  MediaType,
  TextFormat,
  ImageFormat,
  AudioFormat,
  VideoFormat,
  ApplicationFormat,
  ArtifactType,
)

__all__ = [
  "MessageRole",
  "FileSubdirectory", "FileStatus", "FileMimeType",
  "LogLevel", "LogFormat",
  "ModelCapability", "IOType", "SourcePreference",
  "TaskStatus", "TaskEvent",
  "TaskQueueHook",
  "MediaType", "TextFormat", "ImageFormat", "AudioFormat",
  "VideoFormat", "ApplicationFormat",
  "ArtifactType",
]
