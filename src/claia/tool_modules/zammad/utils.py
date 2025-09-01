"""
Utility functions for the Zammad module.

This module provides utility functions and decorators for the Zammad integration.
"""

# External dependencies
import logging
from functools import wraps
from typing import Callable, TypeVar, Tuple, Any, List, Dict, Optional

# Process queue dependencies
from ..lib import Process
from ..lib.enums.agent import ProcessStatus, SourcePreference

# Internal dependencies
from ..cli.settings import Settings
from ..lib.results import Result
from ..lib.files import Conversation, TextFile
from ..lib.enums import MessageRole

# Internal module dependencies
from .api import ZammadAPI
from .settings import ZammadSettings
from .constants import TAG_LIST, TAG_PROMPT, ACCOUNT_MANAGEMENT_PROMPT, VERIFICATION_PROMPT



########################################################################
#                              CONSTANTS                               #
########################################################################
TIMEOUT = 120.0



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar('T')



########################################################################
#                              DECORATORS                              #
########################################################################
def require_zammad_config(func: Callable[..., T]) -> Callable[..., T]:

  """
  Decorator to check if Zammad is properly configured before executing a command.

  Args:
    func: The function to decorate

  Returns:
    The decorated function that checks for Zammad configuration
  """

  @wraps(func)
  def wrapper(self, settings: Settings, *args, **kwargs) -> T:
    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result = Result()
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.success = False
      return result

    # Create Zammad API client and pass it to the function
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Call the original function with the API client
    return func(self, settings, zammad, *args, **kwargs)

  return wrapper



########################################################################
#                              FUNCTIONS                               #
########################################################################
def extract_tag(response: str) -> Tuple[str, bool]:

  """
  Extract tag from AI model response.

  Args:
    response: The AI model response text

  Returns:
    Tuple containing the extracted tag and a success flag
  """

  logger.debug(f"Extracting tag from response of length: {len(response) if response else 0}")
  if not response:
    logger.debug("Empty response received")
    return "Blank", False

  # Remove any escape characters
  cleaned_response = response.replace("\\", "")

  try:
    # Extract tag from [TAG]tag[/TAG] format
    if "[TAG]" in cleaned_response and "[/TAG]" in cleaned_response:
      start = cleaned_response.index("[TAG]") + len("[TAG]")
      end = cleaned_response.index("[/TAG]")
      tag = cleaned_response[start:end].strip()
      logger.debug(f"Found tag: {tag}")

      # Validate tag is in our list
      if tag in TAG_LIST:
        logger.debug(f"Tag '{tag}' is valid")
        return tag, True
      else:
        logger.warning(f"Tag '{tag}' not in valid tag list")
        return "Unknown", False
    else:
      logger.debug("No tag markers found in response")
      return "Blank", False
  except Exception as e:
    logger.error(f"Error extracting tag: {str(e)}")
    return "Error", False


def tag_ticket(
  settings: Settings,
  zammad: ZammadAPI,
  ticket_id: str,
  conversation: Optional[Conversation] = None) -> Tuple[bool, str, str]:

  """
  Process a single ticket for AI tagging.

  Args:
    settings: Application settings
    zammad: ZammadAPI instance
    ticket_id: The ID of the ticket to tag
    conversation: Optional conversation object to record actions

  Returns:
    Tuple of (success flag, tag applied, error message if any)
  """

  logger.debug(f"Processing ticket: {ticket_id}")
  process_queue = ProcessQueue()

  try:
    # Get ticket details
    ticket_details = zammad.get_ticket_details(ticket_id)
    if not ticket_details:
      return False, "", "Could not retrieve ticket details"

    # Create blank conversation object to process tag
    tag_conversation = Conversation(
      settings.files_directory,
      prompt=TAG_PROMPT
    )
    tag_conversation.add_message(
      MessageRole.USER,
      ticket_details
    )

    # Create a process for the request
    logger.debug(f"Creating process for ticket {ticket_id}")
    process = Process(
      agent_type="simple",
      settings=settings,
      conversation=tag_conversation,
      parameters={
        "source_preference": SourcePreference.ANY,
        "model": settings.active_model
      }
    )

    # Add the process to the queue
    process_id = process_queue.put(process)
    logger.debug(f"Added process {process_id} to queue for ticket {ticket_id}")

    # Wait for the process to complete
    completed_process = process_queue.wait_for_process(process_id, timeout=TIMEOUT)

    # Request post processing
    if not completed_process or completed_process.status != ProcessStatus.COMPLETED:
      error_msg = completed_process.error if completed_process else "Process failed or timed out"
      logger.error(f"Process for ticket {ticket_id} failed: {error_msg}")
      return False, "", f"Model error: {error_msg}"
    else:
      logger.debug(f"Process {process_id} completed for ticket {ticket_id}")
      if conversation is not None:
        for message in tag_conversation.get_messages():
          conversation.add_message(
            message.speaker,
            message.content
          )
        conversation.save()

    # Extract and apply tag
    response = tag_conversation.get_latest_message()
    if response and response.content:
      tag, success = extract_tag(response.content)
      logger.debug(f"Extracted tag '{tag}' with success: {success}")

      # Add the appropriate tag
      if success:
        tag_name = f"AI-{tag}"
        logger.debug(f"Adding tag '{tag_name}' to ticket {ticket_id}")
      else:
        tag_name = f"AI-{tag}"
        logger.warning(f"Adding fallback tag '{tag_name}' to ticket {ticket_id}")

      # Apply the tag
      if not zammad.add_tag(ticket_id, tag_name):
        return False, "", f"Failed to add tag {tag_name}"

      # Mark as processed
      logger.debug(f"Marking ticket {ticket_id} as processed")
      if not zammad.add_tag(ticket_id, "AI-Tagged"):
        return False, tag_name, "Added tag but failed to mark as processed"

      return True, tag_name, ""
    else:
      return False, "", "No response generated by the model"

  except Exception as e:
    logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
    return False, "", f"Error: {str(e)}"


def untag_ticket(
  zammad: ZammadAPI,
  ticket_id: str) -> Tuple[int, List[str]]:

  """
  Remove AI tags from a single ticket.

  Args:
    zammad: ZammadAPI instance
    ticket_id: The ID of the ticket
    conversation: Optional conversation object to record actions

  Returns:
    Tuple of (number of tags removed, list of removed tags)
  """

  logger.debug(f"Removing AI tags from ticket {ticket_id}")

  try:
    # Get tags for the ticket
    tags = zammad.list_tags(ticket_id)
    ai_tags = [tag for tag in tags if tag.startswith("AI-")]
    logger.debug(f"Found {len(ai_tags)} AI tags for ticket {ticket_id}")

    # Remove AI tags
    removed_count = 0
    removed_tags = []

    for tag in ai_tags:
      if zammad.remove_tag(ticket_id, tag):
        removed_count += 1
        removed_tags.append(tag)
        logger.debug(f"Removed tag {tag} from ticket {ticket_id}")
      else:
        logger.warning(f"Failed to remove tag {tag} from ticket {ticket_id}")

    logger.info(f"Removed {removed_count} AI tags from ticket {ticket_id}")

    return removed_count, removed_tags

  except Exception as e:
    logger.error(f"Error removing AI tags from ticket {ticket_id}: {str(e)}")
    return 0, []


def find_tickets_by_subject(
  zammad: ZammadAPI,
  subject: str,
  limit: int = 0) -> List[Dict[str, Any]]:

  """
  Find tickets in Zammad that have a specific subject.

  Args:
    zammad: ZammadAPI instance
    subject: The subject line to match (case-insensitive)
    limit: Maximum number of tickets to return (0 for no limit)

  Returns:
    List of matching ticket dictionaries with id, title, created_at, and customer info
  """

  logger.debug(f"Searching for tickets with subject containing: {subject}")

  # Get all open tickets first
  all_tickets = zammad.list_tickets("open-tickets", limit=999, full_response=True)

  if not all_tickets:
    logger.debug("No open tickets found.")
    return []

  matching_tickets = []

  # Check each ticket to see if the subject matches
  for ticket_id in all_tickets:
    ticket_details = zammad.get(f"tickets/{ticket_id}")
    if ticket_details and 'title' in ticket_details:
      # Case-insensitive subject matching
      if subject.lower() in ticket_details['title'].lower():
        matching_tickets.append({
          'id': ticket_id,
          'title': ticket_details['title'],
          'created_at': ticket_details.get('created_at', 'Unknown'),
          'customer': ticket_details.get('customer', 'Unknown')
        })

  # Apply limit if specified
  if limit > 0 and len(matching_tickets) > limit:
    matching_tickets = matching_tickets[:limit]

  logger.debug(f"Found {len(matching_tickets)} tickets with subject containing '{subject}'")
  return matching_tickets


def process_account_ticket(
  settings: Settings,
  zammad: ZammadAPI,
  ticket_id: str,
  file: Optional[TextFile] = None,
  conversation: Optional[Conversation] = None) -> Tuple[bool, str, Optional[TextFile]]:

  """
  Process a single account management ticket and update account list.

  Args:
    settings: Application settings
    zammad: ZammadAPI instance
    ticket_id: The ID of the ticket to process
    file: Optional TextFile instance for the account list
    conversation: Conversation instance

  Returns:
    Tuple of (success flag, error message if any, TextFile instance if successful)
  """

  logger.debug(f"Processing account ticket: {ticket_id}")
  process_queue = ProcessQueue()

  try:
    # Get ticket details
    ticket_details = zammad.get_ticket_details(ticket_id)
    if not ticket_details:
      return False, "Could not retrieve ticket details", None

    # Initialize or load the account list file
    if file is None:
      file = TextFile(settings.files_directory)
    current_account_list = file.get_content()

    # Create account processing conversation
    account_conversation = Conversation(
      settings.files_directory,
      prompt=ACCOUNT_MANAGEMENT_PROMPT
    )
    account_conversation.add_message(
      MessageRole.USER,
      f"Current account list:\n{current_account_list}\n\n\nNew ticket to process:\n{ticket_details}"
    )

    # Create a process for the request
    logger.debug(f"Creating process for account ticket {ticket_id}")
    process = Process(
      agent_type="simple",
      settings=settings,
      conversation=account_conversation,
      parameters={
        "source_preference": SourcePreference.ANY,
        "model": settings.active_model
      }
    )

    # Add the process to the queue
    process_id = process_queue.put(process)
    logger.debug(f"Added process {process_id} to queue for account ticket {ticket_id}")

    # Wait for the process to complete
    completed_process = process_queue.wait_for_process(process_id, timeout=TIMEOUT)

    # Request post processing
    if not completed_process or completed_process.status != ProcessStatus.COMPLETED:
      error_msg = completed_process.error if completed_process else "Process failed or timed out"
      logger.error(f"Process for account ticket {ticket_id} failed: {error_msg}")
      return False, f"Model error: {error_msg}", None

    # Get the model response from the conversation
    response = account_conversation.get_latest_message()
    if not response or not response.content:
      return False, "No response generated by the model", None

    # Copy messages to main conversation if provided
    if conversation is not None:
      for message in account_conversation.get_messages():
        conversation.add_message(
          message.speaker,
          message.content
        )

    previous_account_list = current_account_list
    current_account_list = response.content.strip()

    # Verify no data has been lost in the update
    if previous_account_list:
      logger.debug("Verifying that no data has been lost")

      # Create verification conversation
      verification_conversation = Conversation(
        settings.files_directory,
        prompt=VERIFICATION_PROMPT
      )
      verification_conversation.add_message(
        MessageRole.USER,
        f"Previous list:\n{previous_account_list}\n\nUpdated list:\n{current_account_list}\n\nHas any data been lost? Respond with YES or NO followed by details."
      )

      # Create a process for the verification
      verify_process = Process(
        agent_type="simple",
        settings=settings,
        conversation=verification_conversation,
        parameters={
          "source_preference": SourcePreference.ANY,
          "model": settings.active_model
        }
      )

      # Add the process to the queue
      verify_process_id = process_queue.put(verify_process)
      logger.debug(f"Added verification process {verify_process_id} for account ticket {ticket_id}")

      # Wait for the process to complete
      completed_verify_process = process_queue.wait_for_process(verify_process_id, timeout=TIMEOUT)

      # Process verification results
      if not completed_verify_process or completed_verify_process.status != ProcessStatus.COMPLETED:
        error_msg = completed_verify_process.error if completed_verify_process else "Verification process failed or timed out"
        logger.error(f"Verification for account ticket {ticket_id} failed: {error_msg}")
        return False, f"Verification error: {error_msg}", None

      # Get verification response
      verification_msg = verification_conversation.get_latest_message()
      if not verification_msg or not verification_msg.content:
        return False, "No verification response generated", None

      # Copy verification messages to main conversation if provided
      if conversation is not None:
        for message in verification_conversation.get_messages():
          conversation.add_message(
            message.speaker,
            message.content
          )

      verification_response = verification_msg.content.strip()
      if verification_response.startswith("YES"):
        logger.warning(f"Data loss detected for ticket {ticket_id}: {verification_response}")
        return False, "Data loss detected during processing", None

      logger.debug("Verification passed: No data has been lost")

    # Save the updated content
    file.save(content=current_account_list)

    # Update the file in the conversation if provided
    if conversation is not None:
      conversation.save()

    logger.info(f"Successfully processed account ticket {ticket_id}")
    return True, "", file

  except Exception as e:
    logger.error(f"Error processing account ticket {ticket_id}: {str(e)}")
    return False, f"Error: {str(e)}", None
