"""
Query command class for the CLAIA CLI.

This module contains the command class for sending a one-shot query to the AI.
"""

import logging
import time
from typing import List, Optional, Any

from claia.lib.results import Result
from claia.lib.data.models import Conversation
from claia.lib.enums.conversation import MessageRole
from claia.lib.enums.model import SourcePreference
from claia.lib.process import Process, ProcessStatus
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
      
      # Wait for the process to complete and stream the response
      print()  # Newline before response
      response_content = ""
      
      while process.status == ProcessStatus.PENDING or process.status == ProcessStatus.PROCESSING:
        if process.status == ProcessStatus.PROCESSING:
          response = process.conversation.get_latest_message()
          
          # Only show new content from assistant messages
          if response.message_id != user_message.message_id and response.content:
            if len(response.content) > len(response_content):
              # Print only the new content
              print(response.content[len(response_content):], end='', flush=True)
              response_content = response.content
        
        # Small sleep to avoid busy waiting
        time.sleep(0.1)
      
      print()  # Newline after response
      
      # Check if process completed successfully
      if process.status == ProcessStatus.COMPLETED:
        final_message = process.conversation.get_latest_message()
        
        # Process any tool calls in the final message
        # self._process_tool_calls(final_message, process)
        
        self.logger.debug(f"Query completed successfully: {process_id}")
        # Return success without data since output was already streamed
        return Result(success=True)
      
      elif process.status == ProcessStatus.FAILED:
        error_msg = f"Query failed: {process.error}"
        self.logger.error(error_msg)
        return Result(success=False, message=error_msg)
      
      else:
        error_msg = f"Query ended with unexpected status: {process.status}"
        self.logger.error(error_msg)
        return Result(success=False, message=error_msg)
      
    except Exception as e:
      error_msg = f"Error processing query: {str(e)}"
      self.logger.error(error_msg, exc_info=True)
      return Result(success=False, message=error_msg)
