"""
Conversation settings data model.

Settings control various aspects of conversation behavior,
including streaming, text generation parameters, and image generation parameters.
"""

# External dependencies
from typing import Dict, Any, Optional
import logging


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                        CONVERSATION SETTINGS                         #
########################################################################
class ConversationSettings:
    """
    Class representing settings for a conversation.

    Attributes:
        streaming (bool): Whether to stream responses (default: True)
        text_settings (Dict[str, Any]): Settings for text generation
        image_settings (Dict[str, Any]): Settings for image generation
    """

    def __init__(self,
                 streaming: bool = True,
                 text_settings: Optional[Dict[str, Any]] = None,
                 image_settings: Optional[Dict[str, Any]] = None):
        """
        Initialize conversation settings.

        Args:
            streaming: Whether to stream responses (default: True)
            text_settings: Settings for text generation (default: None)
                - max_tokens: Maximum tokens for text generation
                - temperature: Temperature for text generation
            image_settings: Settings for image generation (default: None)
                - height: Height of generated images
                - width: Width of generated images
                - steps: Number of diffusion steps for image generation
        """
        self.streaming = streaming
        self.text_settings = text_settings or {}
        self.image_settings = image_settings or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the settings to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of settings
        """
        return {
            "streaming": self.streaming,
            "text_settings": self.text_settings,
            "image_settings": self.image_settings
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSettings':
        """
        Create settings from a dictionary.

        Args:
            data: Dictionary containing settings data

        Returns:
            ConversationSettings: New settings object
        """
        return cls(
            streaming=data.get("streaming", True),
            text_settings=data.get("text_settings"),
            image_settings=data.get("image_settings")
        )

