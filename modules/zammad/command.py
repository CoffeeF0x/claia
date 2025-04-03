"""
Zammad integration module command implementation for Claia.

This module provides commands for interacting with the Zammad ticketing system.
"""

# TODO:
# - the untag process sorts oldest tickets first to avoid changing order, but it doesn't consider that some have the ai tag and others don't

# External dependencies
import logging
import os
from typing import Optional

# Internal dependencies
from commands.base import Command, command
from settings import Settings
from results import Result

# Internal dependencies
# from models import run as model_run
from files import Conversation
from enums import MessageRole
from .settings import ZammadSettings
from .api import ZammadAPI
from .constants import ACCOUNT_MANAGEMENT_PROMPT, VERIFICATION_PROMPT
from .utils import require_zammad_config, tag_ticket, untag_ticket, process_account_ticket



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class ZammadCommand(Command):
  """Command class for Zammad ticket management"""

  @command(
    path=["list"],
    description="List tickets from Zammad",
    help_text="List tickets from Zammad based on a query",
    parameters={
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Query name or custom query string (default: open-tickets)",
          "default": "open-tickets"
        }
      }
    },
    returns={
      "type": "string",
      "description": "List of tickets"
    },
    ai_callable=True
  )
  @require_zammad_config
  def list_tickets(self, settings: Settings, zammad: ZammadAPI, query: str = "open-tickets") -> Result:
    """
    List tickets from Zammad based on a query.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      query: Query name or custom query string

    Returns:
      Result: Operation result
    """
    # Create result
    result = Result()

    # Get tickets
    logger.debug("Listing tickets with query: %s", query)
    tickets = zammad.list_tickets(query)

    # Format the response
    if not tickets:
      logger.info("No tickets found for query: %s", query)
      result.message = "No tickets found."
      return result

    logger.info("Found %d tickets for query: %s", len(tickets), query)
    response = f"Found {len(tickets)} tickets:\n\n"
    for ticket_id in tickets:
      response += f"- Ticket ID: {ticket_id}\n"

    result.message = response
    return result

  @command(
    path=["details"],
    description="Get details for a Zammad ticket",
    help_text="Get details for a Zammad ticket using its ID",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket to retrieve"
        }
      },
      "required": ["ticket_id"]
    },
    returns={
      "type": "string",
      "description": "Ticket details"
    },
    ai_callable=True
  )
  @require_zammad_config
  def get_ticket_details(self, settings: Settings, zammad: ZammadAPI, ticket_id: str) -> Result:
    """
    Get details of a specific ticket from Zammad.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to retrieve

    Returns:
      Result: Operation result with ticket details
    """
    # Create result
    result = Result()

    logger.debug("Getting details for ticket ID: %s", ticket_id)

    result.message = zammad.get_ticket_details(ticket_id)
    return result

  @command(
    path=["tag", "add"],
    description="Add a tag to a Zammad ticket",
    help_text="Add a tag to a Zammad ticket",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket to tag"
        },
        "tag": {
          "type": "string",
          "description": "The tag to add to the ticket"
        }
      },
      "required": ["ticket_id", "tag"]
    },
    returns={
      "type": "string",
      "description": "Result message"
    },
    ai_callable=True
  )
  @require_zammad_config
  def add_tag(self, settings: Settings, zammad: ZammadAPI, ticket_id: str, tag: str) -> Result:
    """
    Add a tag to a ticket in Zammad.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to tag
      tag: The tag to add to the ticket

    Returns:
      Result: Operation result
    """
    # Create result
    result = Result()

    logger.debug("Adding tag '%s' to ticket %s", tag, ticket_id)

    tag_result = zammad.add_tag(int(ticket_id), tag)

    if tag_result:
      logger.info("Successfully added tag '%s' to ticket %s", tag, ticket_id)
      result.message = f"Successfully added tag '{tag}' to ticket {ticket_id}."
    else:
      logger.error("Failed to add tag '%s' to ticket %s", tag, ticket_id)
      result.message = f"Failed to add tag '{tag}' to ticket {ticket_id}."
      result.success = False

    return result

  @command(
    path=["tag", "remove"],
    description="Remove a tag from a Zammad ticket",
    help_text="Remove a tag from a Zammad ticket",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket"
        },
        "tag": {
          "type": "string",
          "description": "The tag to remove from the ticket"
        }
      },
      "required": ["ticket_id", "tag"]
    },
    returns={
      "type": "string",
      "description": "Result message"
    },
    ai_callable=True
  )
  @require_zammad_config
  def remove_tag(self, settings: Settings, zammad: ZammadAPI, ticket_id: str, tag: str) -> Result:
    """
    Remove a tag from a ticket in Zammad.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket
      tag: The tag to remove from the ticket

    Returns:
      Result: Operation result
    """
    # Create result
    result = Result()

    logger.debug("Removing tag '%s' from ticket %s", tag, ticket_id)

    tag_result = zammad.remove_tag(int(ticket_id), tag)

    if tag_result:
      logger.info("Successfully removed tag '%s' from ticket %s", tag, ticket_id)
      result.message = f"Successfully removed tag '{tag}' from ticket {ticket_id}."
    else:
      logger.error("Failed to remove tag '%s' from ticket %s", tag, ticket_id)
      result.message = f"Failed to remove tag '{tag}' from ticket {ticket_id}."
      result.success = False

    return result

  @command(
    path=["process", "tag", "single"],
    description="Process a single ticket",
    help_text="Process a single ticket and add AI tags",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket to process"
        },
        "confirm": {
          "type": "boolean",
          "description": "Confirmation to run the process",
          "default": False
        }
      },
      "required": ["ticket_id"]
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def apply_ai_tag(self, settings: Settings, zammad: ZammadAPI, ticket_id: str, confirm: bool = False) -> Result:
    """
    Process a single ticket and add AI tags.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to process
      confirm: Confirmation flag

    Returns:
      Result: Processing result
    """
    result = Result()

    # Require confirmation
    if not confirm:
      result.message = f"This operation will process ticket {ticket_id} and add AI tags. Set confirm=True to proceed."
      result.success = False
      return result

    # Use the utility function to process the ticket
    success, tag, error_msg = tag_ticket(settings, zammad, ticket_id)

    if success:
      result.message = f"Successfully processed ticket {ticket_id} with tag {tag}"
    else:
      result.message = f"Failed to process ticket {ticket_id}: {error_msg}"
      result.success = False

    return result

  @command(
    path=["process", "untag", "single"],
    description="Remove AI tags from a single ticket",
    help_text="Remove AI tags from a specific ticket",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket to untag"
        },
        "confirm": {
          "type": "boolean",
          "description": "Confirmation to run the process",
          "default": False
        }
      },
      "required": ["ticket_id"]
    },
    returns={
      "type": "string",
      "description": "Untagging result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def remove_ai_tags(self, settings: Settings, zammad: ZammadAPI, ticket_id: str, confirm: bool = False) -> Result:
    """
    Remove AI tags from a single ticket.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to untag
      confirm: Confirmation flag

    Returns:
      Result: Untagging result
    """
    result = Result()

    # Require confirmation
    if not confirm:
      result.message = f"This operation will remove AI tags from ticket {ticket_id}. Set confirm=True to proceed."
      result.success = False
      return result

    # Use the utility function to remove tags
    removed_count, removed_tags = untag_ticket(zammad, ticket_id)

    if removed_count > 0:
      removed_list = ", ".join(removed_tags)
      result.message = f"Removed {removed_count} AI tags from ticket {ticket_id}: {removed_list}"
    else:
      result.message = f"No AI tags found for ticket {ticket_id}"

    return result

  @command(
    path=["process", "account", "single"],
    description="Process a single account management ticket",
    help_text="Process a single account management ticket and update account list",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket to process"
        },
        "output_file": {
          "type": "string",
          "description": "File to save the account list to (default: account_list.txt)",
          "default": "account_list.txt"
        },
        "confirm": {
          "type": "boolean",
          "description": "Confirmation to run the process",
          "default": False
        }
      },
      "required": ["ticket_id"]
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def update_account_list(self, settings: Settings, zammad: ZammadAPI, ticket_id: str, output_file: str = "account_list.txt", confirm: bool = False) -> Result:
    """
    Process a single account management ticket and update account list.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to process
      output_file: File to save the account list to
      confirm: Confirmation flag

    Returns:
      Result: Processing result
    """
    result = Result()

    # Require confirmation
    if not confirm:
      result.message = f"This operation will process ticket {ticket_id} and update {output_file}. Set confirm=True to proceed."
      result.success = False
      return result

    # Create or load a conversation
    conversation = Conversation(
      base_directory=settings.conversation_directory,
      files_directory=settings.conversation_files_directory,
      title="Account Management Processing"
    )

    # Use the utility function to process the account ticket
    success, error_msg, file_id = process_account_ticket(
      settings=settings,
      zammad=zammad,
      ticket_id=ticket_id,
      output_file=output_file,
      conversation=conversation
    )

    if success:
      result.message = f"Successfully processed ticket {ticket_id} and updated {output_file}"
    else:
      result.message = f"Failed to process ticket {ticket_id}: {error_msg}"
      result.success = False

    return result

  @command(
    path=["process", "tag"],
    description="Process untagged tickets",
    help_text="Process untagged tickets and add AI tags",
    parameters={
      "type": "object",
      "properties": {
        "confirm": {
          "type": "boolean",
          "description": "Confirmation to run the process",
          "default": False
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of tickets to process",
          "default": 0
        }
      }
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def batch_apply_ai_tags(self, settings: Settings, zammad: ZammadAPI, confirm: bool = False, limit: int = 0) -> Result:
    """
    Process untagged tickets and add AI tags.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      confirm: Confirmation flag
      limit: Maximum number of tickets to process (0 for no limit)

    Returns:
      Result: Processing result
    """
    result = Result()

    # Require confirmation
    if not confirm:
      result.message = "This operation will process untagged tickets and add AI tags. Set confirm=True to proceed."
      result.success = False
      return result

    # Get untagged tickets
    tickets = zammad.list_tickets("untagged-tickets")
    logger.info(f"Found {len(tickets)} untagged tickets")

    # Apply limit if specified
    if limit > 0 and limit < len(tickets):
      logger.info(f"Limiting to {limit} tickets")
      tickets = tickets[:limit]

    if not tickets:
      result.message = "No untagged tickets found."
      return result

    # Process each ticket
    processed_count = 0
    success_count = 0

    for ticket_id in tickets:
      success, tag, error_msg = tag_ticket(settings, zammad, ticket_id)
      processed_count += 1

      if success:
        success_count += 1
        logger.info(f"Successfully tagged ticket {ticket_id} with {tag}")
      else:
        logger.error(f"Failed to tag ticket {ticket_id}: {error_msg}")

    # Return results
    logger.info(f"Completed processing {processed_count} tickets ({success_count} successful)")
    result.message = f"Processed {processed_count} tickets ({success_count} successful)"
    return result

  @command(
    path=["process", "untag"],
    description="Remove AI tags from tickets",
    help_text="Remove AI tags from all tagged tickets",
    parameters={
      "type": "object",
      "properties": {
        "confirm": {
          "type": "boolean",
          "description": "Confirmation to run the process",
          "default": False
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of tickets to process",
          "default": 0
        }
      }
    },
    returns={
      "type": "string",
      "description": "Untagging result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def batch_remove_ai_tags(self, settings: Settings, zammad: ZammadAPI, confirm: bool = False, limit: int = 0) -> Result:
    """
    Remove AI tags from all tagged tickets.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      confirm: Confirmation flag
      limit: Maximum number of tickets to process (0 for no limit)

    Returns:
      Result: Untagging result
    """
    result = Result()

    # Require confirmation
    if not confirm:
      result.message = "This operation will remove AI tags from all tagged tickets. Set confirm=True to proceed."
      result.success = False
      return result

    logger.debug("Starting untag process for all tagged tickets")

    # Get tagged tickets
    tickets = zammad.list_tickets("tagged-tickets")

    if not tickets:
      logger.info("No tagged tickets found")
      result.message = "No tagged tickets found"
      return result

    # Apply limit if specified
    if limit > 0 and limit < len(tickets):
      logger.info(f"Limiting to {limit} tickets")
      tickets = tickets[:limit]

    # Remove AI tags from each ticket
    total_removed = 0
    processed_count = 0

    for ticket_id in tickets:
      removed_count, _ = untag_ticket(zammad, ticket_id)
      total_removed += removed_count
      processed_count += 1

    logger.info(f"Removed {total_removed} AI tags from {processed_count} tickets")
    result.message = f"Completed! Removed {total_removed} AI tags from {processed_count} tickets"
    return result

  @command(
    path=["process", "account"],
    description="Process account management tickets",
    help_text="Process tickets with account management tags and build a list of accounts that need work",
    parameters={
      "type": "object",
      "properties": {
        "output_file": {
          "type": "string",
          "description": "File to save the account list to (default: account_list.txt)",
          "default": "account_list.txt"
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of tickets to process (default: 50)",
          "default": 50
        },
        "confirm": {
          "type": "boolean",
          "description": "Confirmation to run the process",
          "default": False
        }
      }
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def batch_update_account_list(self, settings: Settings, zammad: ZammadAPI, output_file: str = "account_list.txt", limit: int = 50, confirm: bool = False) -> Result:
    """
    Process tickets with account management tags and build a list of accounts that need work.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      output_file: File to save the account list to
      limit: Maximum number of tickets to process
      confirm: Confirmation flag

    Returns:
      Result: Processing result
    """
    result = Result()

    # Require confirmation
    if not confirm:
      result.message = f"This operation will process up to {limit} account management tickets and save results to {output_file}. Set confirm=True to proceed."
      result.success = False
      return result

    # Get tickets matching the account management query
    tickets = zammad.list_tickets("account-management", limit=limit)

    if not tickets:
      result.message = "No account management tickets found."
      return result

    # Create or load a conversation
    conversation = Conversation(
      base_directory=settings.conversation_directory,
      files_directory=settings.conversation_files_directory,
      title="Account Management Processing"
    )

    # Display initial status
    print(f"\n{'='*50}")
    print(f"Starting to process {len(tickets)} account management tickets")
    print(f"{'='*50}\n")

    # Process each ticket
    processed_count = 0
    successful_count = 0
    remaining_tickets = tickets.copy()
    retry_count = {}  # Track how many times each ticket has been retried

    while remaining_tickets:
      # Get the next ticket
      ticket_id = remaining_tickets.pop(0)

      # Track retry attempts
      if ticket_id not in retry_count:
        retry_count[ticket_id] = 0

      # Limit maximum retries per ticket to prevent infinite loops
      max_retries = 3
      if retry_count[ticket_id] >= max_retries:
        print(f"⚠️ Ticket {ticket_id} exceeded maximum retry attempts ({max_retries}). Skipping.")
        continue

      retry_count[ticket_id] += 1

      # Display attempt information
      attempt_info = f" (Retry #{retry_count[ticket_id]})" if retry_count[ticket_id] > 1 else ""
      print(f"\n{'-'*50}")
      print(f"Processing ticket ID: {ticket_id}{attempt_info} ({processed_count+1}/{len(tickets)})")

      # Process the ticket using the utility function
      success, error_msg, _ = process_account_ticket(
        settings=settings,
        zammad=zammad,
        ticket_id=ticket_id,
        output_file=output_file,
        conversation=conversation
      )

      # Handle result
      if success:
        print("✅ Successfully processed ticket")
        successful_count += 1
      else:
        print(f"❌ Error processing ticket {ticket_id}: {error_msg}")
        # Add ticket back to the end of the queue for retry
        if retry_count[ticket_id] < max_retries:
          remaining_tickets.append(ticket_id)
          print(f"Added ticket {ticket_id} back to queue for retry later")

      processed_count += 1

      # Print status information
      print(f"Processed ticket: {ticket_id}")
      print(f"Remaining tickets: {len(remaining_tickets)}")
      print(f"{'-'*50}\n")

    print(f"\n{'='*50}")
    print(f"Processing complete! Successfully processed {successful_count}/{len(tickets)} tickets.")
    print(f"Account list saved to {output_file}")
    print(f"{'='*50}\n")

    result.message = f"Processed {successful_count} tickets. Account list saved to {output_file}"
    return result