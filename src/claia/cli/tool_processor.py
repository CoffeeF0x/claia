"""
Tool processing functionality for CLI - decoupled from conversation.

This module provides functions to detect and process tool calls in conversation output
using the conversation's stored tool pattern and protocol information.
"""

import logging
from typing import Optional, Dict, Any, List

from claia.tools.manager import ToolsManager
from claia.tools.registry import ToolsRegistry
from claia.common.files.conversation import Conversation

logger = logging.getLogger(__name__)


class ToolProcessor:
  """Handles tool call detection and processing for CLI."""

  def __init__(self):
    self.tools_manager = ToolsManager()
    self.tools_registry = ToolsRegistry(self.tools_manager)

  def has_tool_call_tokens(self, content: str, conversation: Conversation) -> bool:
    """
    Check if content contains tool calling opening tokens based on conversation's pattern.

    Args:
        content: The content to check
        conversation: Conversation object with tool pattern info

    Returns:
        bool: True if content contains tool calling opening tokens
    """
    if not conversation.tool_pattern_name:
      return False

    try:
      self.tools_manager.load_all()
      pattern_plugin, pattern_info = self.tools_manager.get_pattern_by_name(conversation.tool_pattern_name)

      if not pattern_plugin or not pattern_info:
        logger.debug(f"Pattern '{conversation.tool_pattern_name}' not found")
        return False

      # Check for any opening tokens in the content
      for token in pattern_info.opening_tokens:
        if token in content:
          return True

      return False

    except Exception as e:
      logger.warning(f"Error checking for tool call tokens: {e}")
      return False

  def process_message_content(self, content: str, conversation: Conversation, settings=None, **kwargs) -> str:
    """
    Process tool calls in message content using conversation's tool configuration.

    Args:
        content: The content to process
        conversation: Conversation object with tool configuration
        settings: Optional settings object
        **kwargs: Additional kwargs to pass to tools

    Returns:
        str: Processed content with tool calls executed
    """
    if not conversation.tool_pattern_name or not conversation.tool_protocol_name:
      logger.debug("No tool pattern or protocol configured for conversation")
      return content

    try:
      return self.tools_registry.process_content(
        conversation,
        content,
        settings=settings,
        protocol_name=conversation.tool_protocol_name,
        **kwargs
      )
    except Exception as e:
      logger.error(f"Tool processing failed: {e}")
      return content

  def check_and_process_if_needed(self, content: str, conversation: Conversation, settings=None, **kwargs) -> str:
    """
    Check if content has tool calls and process them if found.

    Args:
        content: The content to check and potentially process
        conversation: Conversation object with tool configuration
        settings: Optional settings object
        **kwargs: Additional kwargs to pass to tools

    Returns:
        str: Original content if no tool calls, processed content if tool calls found
    """
    if self.has_tool_call_tokens(content, conversation):
      logger.debug("Tool call tokens detected, processing...")
      return self.process_message_content(content, conversation, settings, **kwargs)

    return content
