"""
Utility functions for the Zammad module.

This module provides utility functions and decorators for the Zammad integration.
"""

# External dependencies
import logging
import os
from functools import wraps
from typing import Callable, TypeVar, Tuple, Any, List, Dict, Optional

# Internal dependencies
from settings import Settings
from results import Result
from files import Conversation
from enums import MessageRole

# Internal module dependencies
from .api import ZammadAPI
from .settings import ZammadSettings
from .constants import TAG_LIST, TAG_PROMPT, ACCOUNT_MANAGEMENT_PROMPT, VERIFICATION_PROMPT
# from models import run as model_run



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
  logger.debug("Extracting tag from response of length: %d", len(response) if response else 0)
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
      logger.debug("Found tag: %s", tag)

      # Validate tag is in our list
      if tag in TAG_LIST:
        logger.debug("Tag '%s' is valid", tag)
        return tag, True
      else:
        logger.warning("Tag '%s' not in valid tag list", tag)
        return "Unknown", False
    else:
      logger.debug("No tag markers found in response")
      return "Blank", False
  except Exception as e:
    logger.error("Error extracting tag: %s", str(e))
    return "Error", False


def tag_ticket(settings: Settings, zammad: ZammadAPI, ticket_id: str) -> Tuple[bool, str, str]:
  """
  Process a single ticket for AI tagging.

  Args:
    settings: Application settings
    zammad: ZammadAPI instance
    ticket_id: The ID of the ticket to tag

  Returns:
    Tuple of (success flag, tag applied, error message if any)
  """
  logger.debug(f"Processing ticket: {ticket_id}")

  try:
    # Get ticket details
    ticket_details = zammad.get_ticket_details(ticket_id)
    if not ticket_details:
      return False, "", "Could not retrieve ticket details"

    # Prepare messages for the AI model
    tagging_messages = [
      {"role": "system", "content": TAG_PROMPT},
      {"role": "user", "content": ticket_details}
    ]

    # Run the AI model to get tag
    logger.debug(f"Running AI model for ticket {ticket_id}")
    tagging_result = model_run(settings.active_model, tagging_messages, settings=settings)

    if tagging_result.is_error():
      error_msg = tagging_result.get_message()
      logger.error(f"Error running tagging model for ticket {ticket_id}: {error_msg}")
      return False, "", f"Model error: {error_msg}"

    # Extract and apply tag
    if tagging_result.data:
      tag, success = extract_tag(tagging_result.data)
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


def untag_ticket(zammad: ZammadAPI, ticket_id: str) -> Tuple[int, List[str]]:
  """
  Remove AI tags from a single ticket.

  Args:
    zammad: ZammadAPI instance
    ticket_id: The ID of the ticket

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


def process_account_ticket(settings: Settings, zammad: ZammadAPI,
                    ticket_id: str, output_file: str,
                    conversation: Conversation) -> Tuple[bool, str, Optional[int]]:
  """
  Process a single account management ticket and update account list.

  Args:
    settings: Application settings
    zammad: ZammadAPI instance
    ticket_id: The ID of the ticket to process
    output_file: Path to the account list file
    conversation: Conversation instance

  Returns:
    Tuple of (success flag, error message if any, file_id if successful)
  """
  logger.debug(f"Processing account ticket: {ticket_id}")

  try:
    # Get ticket details
    ticket_details = zammad.get_ticket_details(ticket_id)
    if not ticket_details:
      return False, "Could not retrieve ticket details", None

    # Initialize or load the account list file
    file_id = None
    current_account_list = ""

    if os.path.exists(output_file):
      logger.debug(f"Loading existing account list from {output_file}")
      file_id = conversation.add_file(output_file)
      account_file = conversation.get_file(file_id)
      if account_file and hasattr(account_file, 'get_preview'):
        current_account_list = account_file.get_preview()
    else:
      logger.debug(f"Creating new account list file: {output_file}")
      # Create an empty file
      with open(output_file, "w") as f:
        f.write("")
      file_id = conversation.add_file(output_file)

    # Prepare optimized messages for the LLM
    account_messages = [
      {"role": "system", "content": ACCOUNT_MANAGEMENT_PROMPT},
      {"role": "user", "content": f"Current account list:\n{current_account_list}\n\n\nNew ticket to process:\n{ticket_details}"}
    ]

    # Run the AI model to update the account list
    logger.debug(f"Sending ticket {ticket_id} to LLM for processing")
    model_result = model_run(settings.active_model, account_messages, settings=settings)

    if model_result.is_error():
      error_msg = model_result.get_message()
      logger.error(f"Error processing ticket {ticket_id}: {error_msg}")
      return False, f"Model error: {error_msg}", None

    # Update account list with model's response
    if not model_result.data:
      return False, "No response generated by the model", None

    previous_account_list = current_account_list
    current_account_list = model_result.data.strip()

    # Verify no data has been lost in the update
    if previous_account_list:
      logger.debug("Verifying that no data has been lost")
      verification_messages = [
        {"role": "system", "content": VERIFICATION_PROMPT},
        {"role": "user", "content": f"Previous list:\n{previous_account_list}\n\nUpdated list:\n{current_account_list}\n\nHas any data been lost? Respond with YES or NO followed by details."}
      ]

      verification_result = model_run(settings.active_model, verification_messages, settings=settings)

      if verification_result.is_error():
        error_msg = verification_result.get_message()
        logger.error(f"Error during verification for ticket {ticket_id}: {error_msg}")
        return False, f"Verification error: {error_msg}", None

      verification_response = verification_result.data.strip() if verification_result.data else ""
      if verification_response.startswith("YES"):
        logger.warning(f"Data loss detected for ticket {ticket_id}: {verification_response}")
        return False, "Data loss detected during processing", None

      logger.debug("Verification passed: No data has been lost")

    # Save the updated content
    with open(output_file, "w") as f:
      f.write(current_account_list)

    # Update the file in the conversation
    file_id = conversation.add_file(output_file)

    # Add a message to the conversation about the update
    conversation.add_message(
      role=MessageRole.SYSTEM,
      content=f"Updated account list after processing ticket {ticket_id}"
    )

    # Save the conversation state
    conversation.save()

    logger.info(f"Successfully processed account ticket {ticket_id}")
    return True, "", file_id

  except Exception as e:
    logger.error(f"Error processing account ticket {ticket_id}: {str(e)}")
    return False, f"Error: {str(e)}", None