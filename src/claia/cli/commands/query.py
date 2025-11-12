"""
Query command class for the CLAIA CLI.

This module contains the command class for sending a one-shot query to the AI.
"""

import logging
from typing import List, Optional, Any

from claia.lib.results import Result
from claia.lib.data.models import Conversation
from claia.lib.enums.conversation import MessageRole
from claia.lib.enums.model import SourcePreference
from claia.lib.process import Process
from claia.cli.utils import stream_process_response
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Default agent to use if none is active
DEFAULT_AGENT = "assistant"


class QueryCommand(BaseCommand):
  """Command to send a one-shot query to the AI."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the query command - send a message and get a response.
    
    Args:
        args: List of arguments (the query text)
        conversation: Optional conversation context (unused, we use active conversation)
    
    Returns:
        Result with the AI's response
    """
    self.logger.debug("Query command received")
    
    if not args:
      output = f"Missing query text. Usage: {self.format_command('query <your question>')}"
      return Result(success=False, message=output)
    
    # Join all args into the query text
    query_text = ' '.join(args)
    
    try:
      # Ensure we have an active conversation
      if not self.settings.active_conversation:
        self.settings.active_conversation = Conversation()
        self.logger.debug("Created new conversation for query")
      
      # Ensure we have an active agent
      if not self.settings.active_agent:
        self.settings.active_agent = self.settings.default_agent or DEFAULT_AGENT
        self.logger.debug(f"Using agent: {self.settings.active_agent}")
      
      # Add the user message to the conversation
      user_message = self.settings.active_conversation.add_message(
        MessageRole.USER, 
        query_text
      )
      
      # Get user configuration parameters
      user_kwargs = self.settings.get_user_kwargs()
      
      # Create a process for the query
      process = Process(
        agent_type=self.settings.active_agent,
        conversation=self.settings.active_conversation,
        parameters={
          "source_preference": SourcePreference.ANY,
          "model_id": self.settings.active_model,
          **user_kwargs
        }
      )
      
      # Add process to registry for execution
      process_id = self.registry.add_process(process)
      self.logger.debug(f"Query process added with ID: {process_id}")
      
      # Stream the response and handle completion
      success = stream_process_response(
        process=process,
        user_message_id=user_message.message_id,
        file_repo=None,  # Don't save conversation for query command
        save_conversation=False
      )
      
      if success:
        self.logger.debug(f"Query completed successfully: {process_id}")
        return Result(success=True)
      else:
        error_msg = f"Query failed with status: {process.status}"
        self.logger.error(error_msg)
        return Result(success=False, message=error_msg)
      
    except Exception as e:
      error_msg = f"Error processing query: {str(e)}"
      self.logger.error(error_msg, exc_info=True)
      return Result(success=False, message=error_msg)
