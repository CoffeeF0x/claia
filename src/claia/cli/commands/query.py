"""
Query command for sending one-shot queries to the AI.
"""

import logging
import threading
from typing import List, Optional, Any

from claia.lib.results import Result
from claia.lib.data.models import Conversation
from claia.lib.enums.conversation import MessageRole
from claia.lib.enums.model import SourcePreference
from claia.lib.process import Process
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
      if not self.settings.active_conversation:
        self.settings.active_conversation = Conversation()
      
      if not self.settings.active_agent:
        self.settings.active_agent = self.settings.default_agent or DEFAULT_AGENT
      
      self.settings.active_conversation.add_message(MessageRole.USER, query_text)
      user_kwargs = self.settings.get_user_kwargs()
      
      done_event = threading.Event()
      error_holder = [None]

      process = Process(
        agent_type=self.settings.active_agent,
        conversation=self.settings.active_conversation,
        parameters={
          "source_preference": SourcePreference.ANY,
          "model_id": self.settings.active_model,
          **user_kwargs
        }
      )

      process.on("token", lambda token: print(token, end='', flush=True))

      def on_complete(full_response):
        if full_response and not full_response.endswith('\n'):
          print()
        done_event.set()

      def on_error(error_msg):
        error_holder[0] = error_msg
        print(f"\nError: {error_msg}")
        done_event.set()

      process.on("complete", on_complete)
      process.on("error", on_error)
      
      self.registry.add_process(process)
      done_event.wait()

      if error_holder[0]:
        return Result(success=False, message=f"Query failed: {error_holder[0]}")
      return Result(success=True)
      
    except Exception as e:
      self.logger.error(f"Error processing query: {e}", exc_info=True)
      return Result(success=False, message=f"Error processing query: {str(e)}")
