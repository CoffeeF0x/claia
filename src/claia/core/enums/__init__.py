"""
Domain enums for claia.core.

These enums describe roles, statuses, and capability flags used across
the data models and runtime.
"""

from .agent import AgentStatus
from .conversation import MessageRole
from .events import EventType
from .file import FileSubdirectory, FileStatus, FileMimeType
from .logging import LogLevel, LogFormat
from .model import ModelCapability, IOType, SourcePreference
from .parser import TagType
from .plugins import ParamScope, ParamCategory
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
  "AgentStatus",
  "MessageRole",
  "EventType",
  "FileSubdirectory", "FileStatus", "FileMimeType",
  "LogLevel", "LogFormat",
  "ModelCapability", "IOType", "SourcePreference",
  "TagType",
  "ParamScope", "ParamCategory",
  "TaskStatus", "TaskEvent",
  "TaskQueueHook",
  "MediaType", "TextFormat", "ImageFormat", "AudioFormat",
  "VideoFormat", "ApplicationFormat",
  "ArtifactType",
]
