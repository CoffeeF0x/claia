"""
Utility functions for the CLAIA CLI.

This module contains reusable utility functions for common CLI operations.
"""

import time
import logging
from typing import Optional

from claia.lib.process import Process, ProcessStatus
from claia.lib.data import FileSystemRepository


logger = logging.getLogger(__name__)


def stream_process_response(
    process: Process,
    user_message_id: str,
    file_repo: Optional[FileSystemRepository] = None,
    save_conversation: bool = True
) -> bool:
  """
  Stream the response from a process as it completes.
  
  This function waits for a process to complete and streams the response content
  to stdout as it arrives. It handles all process statuses (COMPLETED, FAILED, CANCELLED).
  
  Args:
      process: The Process object to monitor
      user_message_id: The ID of the user message (to avoid displaying it)
      file_repo: Optional FileSystemRepository for saving conversations
      save_conversation: Whether to save the conversation after completion (default: True)
  
  Returns:
      bool: True if process completed successfully, False otherwise
  """
  new_content = ""
  response = None
  
  # Wait for the process to complete and stream updates
  while process.status == ProcessStatus.PENDING or process.status == ProcessStatus.PROCESSING:
    if process.status == ProcessStatus.PROCESSING:
      response = process.conversation.get_latest_message()
      
      # Only show new content from assistant messages
      if response.message_id != user_message_id:
        if new_content and response.content and len(response.content) > len(new_content):
          # Print only the new content since last update
          print(response.content[len(new_content):], end='', flush=True)
        elif not new_content and response.content:
          # First content, print it all
          print(response.content, end='', flush=True)
        
        new_content = response.content or ""
    
    # Sleep to avoid busy waiting
    time.sleep(0.1)
  
  logger.debug(f"Process completed with status: {process.status}")
  
  # Handle the final result based on status
  if process.status == ProcessStatus.COMPLETED:
    final_message = process.conversation.get_latest_message()
    
    # Display any remaining content that wasn't streamed yet
    if new_content:
      remaining_content = final_message.content[len(new_content):]
      if remaining_content:
        print(remaining_content, end='', flush=True)
    else:
      # No content was streamed, print the full message
      print(final_message.content, end='', flush=True)
    
    # Add newline after final message if it doesn't already end with one
    if final_message.content and not final_message.content.endswith('\n'):
      print()
    
    # Save conversation if requested and file_repo is provided
    if save_conversation and file_repo:
      if not file_repo.save(process.conversation):
        logger.error("Failed to save conversation")
    
    return True
    
  elif process.status == ProcessStatus.FAILED:
    logger.error(f"Process failed: {process.error}")
    print(f"\nError: {process.error}")
    return False
    
  elif process.status == ProcessStatus.CANCELLED:
    logger.warning(f"Process cancelled: {process.error}")
    print("\nProcess was cancelled.")
    return False
  
  # Unknown status
  logger.error(f"Process ended with unexpected status: {process.status}")
  print(f"\nUnexpected process status: {process.status}")
  return False
