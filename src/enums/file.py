"""
This module defines enums related to file operations in CLAIA.
"""

# External dependencies
from enum import Enum, auto



########################################################################
#                          FILE SUBDIRECTORIES                         #
########################################################################
class FileSubdirectory(Enum):
    """Enum for file subdirectories used in file storage."""
    TEXT = "text"
    IMAGE = "images"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "documents"
    SPREADSHEET = "spreadsheets"
    PRESENTATION = "presentations"
    ARCHIVE = "archives"
    MISC = "misc"

    @classmethod
    def from_mime_type(cls, mime_type: str) -> 'FileSubdirectory':
        """Get the appropriate subdirectory based on MIME type."""
        if mime_type.startswith("text/") or mime_type in ["application/json", "application/xml"]:
            return cls.TEXT
        elif mime_type.startswith("image/"):
            return cls.IMAGE
        elif mime_type.startswith("audio/"):
            return cls.AUDIO
        elif mime_type.startswith("video/"):
            return cls.VIDEO
        elif mime_type in ["application/pdf", "application/msword", 
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return cls.DOCUMENT
        elif mime_type in ["application/vnd.ms-excel", 
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return cls.SPREADSHEET
        elif mime_type in ["application/vnd.ms-powerpoint", 
                         "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
            return cls.PRESENTATION
        elif mime_type in ["application/zip", "application/x-rar-compressed", 
                         "application/x-tar", "application/gzip"]:
            return cls.ARCHIVE
        else:
            return cls.MISC



########################################################################
#                            FILE STATUS                               #
########################################################################
class FileStatus(Enum):
    """Enum for tracking file status in the system."""
    ACTIVE = auto()        # File is active and in use
    DELETED = auto()       # File is marked for deletion
    TEMPORARY = auto()     # Temporary file that can be cleaned up
    EXTERNAL = auto()      # External file (reference only) 