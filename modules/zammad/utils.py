"""
Utility functions for the Zammad module.

This module provides utility functions and decorators for the Zammad integration.
"""

# External dependencies
import logging
import os
from functools import wraps
from typing import Callable, TypeVar, Tuple, Any

# Internal dependencies
from settings import Settings
from results import Result

# Internal module dependencies
from .api import ZammadAPI
from .settings import ZammadSettings
from .constants import TAG_LIST, TAG_PROMPT
from models import run as model_run



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
      result.status = "error"
      return result

    # Create Zammad API client and pass it to the function
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Call the original function with the API client
    return func(self, settings, zammad, *args, **kwargs)

  return wrapper



########################################################################
#                              FUNCTIONS                               #
########################################################################
def extract_tag_from_response(response: str) -> Tuple[str, bool]:
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


def zammad_run_process(settings: Settings, zammad: ZammadAPI) -> Result:
  """
  Process untagged tickets and add AI tags.

  Args:
    settings: Application settings
    zammad: ZammadAPI instance

  Returns:
    Result object
  """
  logger.debug("Starting Zammad ticket processing")

  result = Result()
  tickets = zammad.list_tickets("untagged-tickets")
  logger.info("Found %d untagged tickets", len(tickets))

  # For testing, limit to a subset of tickets
  temp_tickets = tickets[11:] if len(tickets) > 11 else tickets
  logger.debug("Processing subset of %d tickets", len(temp_tickets))

  processed_count = 0
  for ticket_id in temp_tickets:
    logger.debug("Processing ticket ID: %s", ticket_id)
    # Get ticket details
    ticket_details = zammad.get_ticket_details(ticket_id)

    # Prepare messages for the AI model
    tagging_messages = [
      {"role": "system", "content": TAG_PROMPT},
      {"role": "user", "content": ticket_details}
    ]

    logger.debug("Running AI model for ticket %s", ticket_id)
    # Run the AI model to get tag
    tagging_result = model_run(settings.active_model, tagging_messages, settings=settings)

    if tagging_result.is_error():
      logger.error("Error running tagging model for ticket %s: %s", ticket_id, tagging_result.get_message())
      continue

    logger.debug("AI model response for ticket %s: %s", ticket_id, tagging_result.data)

    # Extract and apply tag
    if tagging_result.data:
      tag, success = extract_tag_from_response(tagging_result.data)
      logger.debug("Extracted tag '%s' with success: %s", tag, success)

      # Add the appropriate tag
      if success:
        logger.debug("Adding AI tag '%s' to ticket %s", tag, ticket_id)
        zammad.add_tag(ticket_id, f"AI-{tag}")
      else:
        logger.warning("Adding fallback tag '%s' to ticket %s", tag, ticket_id)
        zammad.add_tag(ticket_id, f"AI-{tag}")

      # Mark as processed
      logger.debug("Marking ticket %s as processed", ticket_id)
      zammad.add_tag(ticket_id, "AI-Tagged")
      processed_count += 1

  logger.info("Completed processing %d tickets", processed_count)
  result.message = f"Processed {processed_count} tickets"
  return result