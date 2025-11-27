"""
Query command for sending one-shot queries to the AI.
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
DEFAULT_AGENT = "assistant"


class QueryCommand(BaseCommand):
  """Command to send a one-shot query to the AI."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Send a message and get a response."""
    if not args:
      return Result(success=False, message=f"Missing query text. Usage: {self.format_command('query <your question>')}")
    
    query_text = ' '.join(args)
    
    try:
      # Ensure conversation and agent exist
      if not self.settings.active_conversation:
        self.settings.active_conversation = Conversation()
      
      if not self.settings.active_agent:
        self.settings.active_agent = self.settings.default_agent or DEFAULT_AGENT
      
      # Add user message
      user_message = self.settings.active_conversation.add_message(MessageRole.USER, query_text)
      user_kwargs = self.settings.get_user_kwargs()
      
      # Create and run process
      process = Process(
        agent_type=self.settings.active_agent,
        conversation=self.settings.active_conversation,
        parameters={
          "source_preference": SourcePreference.ANY,
          "model_id": self.settings.active_model,
          **user_kwargs
        }
      )
      
      self.registry.add_process(process)
      
      success = stream_process_response(
        process=process,
        user_message_id=user_message.message_id,
        file_repo=None,
        save_conversation=False
      )
      
      if success:
        return Result(success=True)
      return Result(success=False, message=f"Query failed with status: {process.status}")
      
    except Exception as e:
      self.logger.error(f"Error processing query: {e}", exc_info=True)
      return Result(success=False, message=f"Error processing query: {str(e)}")
