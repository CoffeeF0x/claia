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
from datetime import datetime

# Internal dependencies
from claia.commands.base import Command, command
from claia.cli.settings import Settings
from claia.lib.results import Result

# Internal dependencies
# from models import run as model_run
from files import Conversation
from enums import MessageRole
from .settings import ZammadSettings
from .api import ZammadAPI
from .constants import ACCOUNT_MANAGEMENT_PROMPT, VERIFICATION_PROMPT, TICKET_QUERIES
from .utils import require_zammad_config, tag_ticket, untag_ticket, process_account_ticket, find_tickets_by_subject



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
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of tickets to display (default: 99)",
          "default": 99
        },
        "compact": {
          "type": "boolean",
          "description": "Show compact view without detailed ticket information",
          "default": False
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
  def list_tickets(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    query: str = "open-tickets",
    limit: int = 99,
    compact: bool = False) -> Result:

    """
    List tickets from Zammad based on a query.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      query: Query name or custom query string
      limit: Maximum number of tickets to display
      compact: Show compact view without detailed ticket information

    Returns:
      Result: Operation result
    """

    result = Result()

    # Get tickets - API now returns detailed info by default
    logger.debug(f"Listing tickets with query: {query}, limit: {limit}, compact: {compact}")
    tickets = zammad.list_tickets(query)

    # Format the response
    if not tickets:
      logger.info(f"No tickets found for query: {query}")
      result.message = "No tickets found."
      return result

    # Apply limit after we get the count
    total_tickets = len(tickets)
    if limit > 0 and limit < total_tickets:
      tickets = tickets[:limit]

    # Build header
    query_display = query
    if query in TICKET_QUERIES:
      query_display = f"{query} ({TICKET_QUERIES[query]})"

    response = [f"┌{'─' * 78}┐"]
    response.append(f"│ {'ZAMMAD TICKETS':^76} │")
    response.append(f"├{'─' * 78}┤")
    response.append(f"│ Query: {query_display:<68} │")
    response.append(f"│ Found {total_tickets} tickets, showing {len(tickets)}{'':^41} │")
    response.append(f"├{'─' * 78}┤")

    if compact:
      for ticket in tickets:
        title = ticket.get('title', 'Unknown')
        if len(title) > 60:
          title = title[:57] + '...'
        response.append(f"│ #{ticket['id']} - {title:<{69 - len(str(ticket['id']))}} │")
    else:
      # Add column headers for detailed view
      response.append(f"│ {'ID':<5}│ {'TITLE':<30}│ {'CREATED':<20}│ {'STATE':<15} │")
      response.append(f"├{'─' * 5}┼{'─' * 30}┼{'─' * 20}┼{'─' * 15}┤")

      # Add ticket rows
      for ticket in tickets:
        # Truncate long titles
        title = ticket.get('title', 'Unknown')
        if len(title) > 27:
          title = title[:27] + '...'
        else:
          title = title.ljust(30)

        # Format dates
        created_at = ticket.get('created_at', '')
        if created_at:
          try:
            # Parse ISO format to datetime and convert to cleaner format
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            created_at = dt.strftime('%Y-%m-%d %H:%M')
          except Exception:
            pass

        # Get state name if available
        state = ticket.get('state', str(ticket.get('state_id', 'Unknown')))

        response.append(f"│ {ticket['id']:<5}│ {title:<30}│ {created_at:<20}│ {state:<15} │")

    response.append(f"└{'─' * 78}┘")

    # Add a note about the details command
    response.append("\nTo view details for a specific ticket:")
    response.append("claia zammad details <ticket_id>")

    # Add a note about detailed view if not already using it
    if compact and total_tickets > 0:
      response.append("\nFor more detailed view:")
      response.append(f"claia zammad list {query} --compact")

    result.message = "\n".join(response)
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
        },
        "compact": {
          "type": "boolean",
          "description": "Show compact view without full message bodies",
          "default": False
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
  def get_ticket_details(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    ticket_id: str,
    compact: bool = False) -> Result:

    """
    Get details of a specific ticket from Zammad.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to retrieve
      compact: Show compact view without full message bodies

    Returns:
      Result: Operation result with ticket details
    """

    result = Result()

    logger.debug(f"Getting details for ticket ID: {ticket_id}")

    # The formatting is now handled in the API layer
    result.message = zammad.get_ticket_details(ticket_id, compact)

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
  def add_tag(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    ticket_id: str,
    tag: str) -> Result:

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

    result = Result()

    logger.debug(f"Adding tag '{tag}' to ticket {ticket_id}")

    tag_result = zammad.add_tag(int(ticket_id), tag)

    if tag_result:
      logger.info(f"Successfully added tag '{tag}' to ticket {ticket_id}")
      result.message = f"Successfully added tag '{tag}' to ticket {ticket_id}."
    else:
      logger.error(f"Failed to add tag '{tag}' to ticket {ticket_id}")
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
  def remove_tag(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    ticket_id: str,
    tag: str) -> Result:

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

    result = Result()

    logger.debug(f"Removing tag '{tag}' from ticket {ticket_id}")

    tag_result = zammad.remove_tag(int(ticket_id), tag)

    if tag_result:
      logger.info(f"Successfully removed tag '{tag}' from ticket {ticket_id}")
      result.message = f"Successfully removed tag '{tag}' from ticket {ticket_id}."
    else:
      logger.error(f"Failed to remove tag '{tag}' from ticket {ticket_id}")
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
  def apply_ai_tag(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    ticket_id: str,
    confirm: bool = False) -> Result:

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
    success, tag, error_msg = tag_ticket(
      settings=settings,
      zammad=zammad,
      ticket_id=ticket_id,
      conversation=Conversation(settings.files_directory, title=f"Ticket {ticket_id} Tagging")
    )

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
  def remove_ai_tags(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    ticket_id: str,
    confirm: bool = False) -> Result:

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
  def update_account_list(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    ticket_id: str,
    output_file: str = "account_list.txt",
    confirm: bool = False) -> Result:

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
      settings.files_directory,
      title=f"Ticket {ticket_id} Account Management"
    )

    # Use the utility function to process the account ticket
    success, error_msg, file = process_account_ticket(
      settings=settings,
      zammad=zammad,
      ticket_id=ticket_id,
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
  def batch_apply_ai_tags(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    confirm: bool = False,
    limit: int = 0) -> Result:

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
      success, tag, error_msg = tag_ticket(
        settings=settings,
        zammad=zammad,
        ticket_id=ticket_id,
        conversation=Conversation(settings.files_directory, title=f"Batch Ticket Tagging")
      )
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
  def batch_remove_ai_tags(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    confirm: bool = False,
    limit: int = 0) -> Result:

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
  def batch_update_account_list(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    output_file: str = "account_list.txt",
    limit: int = 50,
    confirm: bool = False) -> Result:

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
      settings.files_directory,
      title="Batch Account Management"
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
    file = TextFile(settings.files_directory)

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
      success, error_msg, file = process_account_ticket(
        settings=settings,
        zammad=zammad,
        ticket_id=ticket_id,
        file=file,
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


  @command(
    path=["find", "subject"],
    description="Find Zammad tickets with a specific subject",
    help_text="Find and display Zammad tickets that have a specific subject line",
    parameters={
      "type": "object",
      "properties": {
        "subject": {
          "type": "string",
          "description": "The subject line to match (case-insensitive)"
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of tickets to display (0 for no limit)",
          "default": 0
        },
        "show_details": {
          "type": "boolean",
          "description": "Whether to show full details of the first ticket",
          "default": False
        }
      },
      "required": ["subject"]
    },
    returns={
      "type": "string",
      "description": "Search results"
    },
    ai_callable=True
  )
  @require_zammad_config
  def find_tickets_by_subject(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    subject: str,
    limit: int = 0,
    show_details: bool = False) -> Result:

    """
    Find tickets in Zammad that have a specific subject.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      subject: The subject line to match (case-insensitive)
      limit: Maximum number of tickets to display (0 for no limit)
      show_details: Whether to show full details of the first ticket

    Returns:
      Result: Search results
    """

    result = Result()

    # Use the shared utility function to find matching tickets
    matching_tickets = find_tickets_by_subject(zammad, subject, limit)

    # No matching tickets found
    if not matching_tickets:
      logger.info(f"No tickets found with subject containing '{subject}'")
      result.message = f"No tickets found with subject containing '{subject}'."
      return result

    # Display what was found
    logger.info(f"Found {len(matching_tickets)} tickets with subject containing '{subject}'")

    # Format the response
    response = f"Found {len(matching_tickets)} tickets with subject containing '{subject}':\n\n"

    # Show full details of the first ticket if requested
    if show_details and matching_tickets:
      first_ticket = matching_tickets[0]
      response += f"First matching ticket details:\n"
      response += f"{zammad.get_ticket_details(first_ticket['id'])}\n\n"
      response += f"{'='*50}\n\nAll matching tickets:\n\n"

    # List all matching tickets
    for idx, ticket in enumerate(matching_tickets, 1):
      response += f"{idx}. ID: {ticket['id']} - {ticket['title']}\n"
      response += f"   Created: {ticket['created_at']}\n"
      if ticket.get('customer'):
        response += f"   Customer: {ticket['customer']}\n"
      response += "\n"

    # Add a reminder about the delete command
    response += f"\nTo delete these tickets, use: claia zammad delete subject \"{subject}\" --confirm"

    result.message = response
    return result


  @command(
    path=["delete", "subject"],
    description="Delete Zammad tickets with a specific subject",
    help_text="Delete Zammad tickets that have a specific subject line",
    parameters={
      "type": "object",
      "properties": {
        "subject": {
          "type": "string",
          "description": "The subject line to match (case-insensitive)"
        },
        "confirm": {
          "type": "boolean",
          "description": "Confirmation to run the deletion process",
          "default": False
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of tickets to process (0 for no limit)",
          "default": 0
        }
      },
      "required": ["subject"]
    },
    returns={
      "type": "string",
      "description": "Deletion result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def delete_tickets_by_subject(
    self,
    settings: Settings,
    zammad: ZammadAPI,
    subject: str,
    confirm: bool = False,
    limit: int = 0) -> Result:

    """
    Delete tickets from Zammad that have a specific subject.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      subject: The subject line to match (case-insensitive)
      confirm: Confirmation flag
      limit: Maximum number of tickets to process (0 for no limit)

    Returns:
      Result: Deletion result
    """

    result = Result()

    # Require confirmation
    if not confirm:
      result.message = f"This operation will delete tickets with subject: '{subject}'. Set confirm=True to proceed."
      result.success = False
      return result

    # Use the shared utility function to find matching tickets
    matching_tickets = find_tickets_by_subject(zammad, subject, limit)

    # No matching tickets found
    if not matching_tickets:
      logger.info(f"No tickets found with subject containing '{subject}'")
      result.message = f"No tickets found with subject containing '{subject}'."
      return result

    # Display what will be deleted
    logger.info(f"Found {len(matching_tickets)} tickets with subject containing '{subject}'")

    # Delete each matching ticket
    deleted_count = 0
    for ticket in matching_tickets:
      try:
        logger.info(f"Deleting ticket {ticket['id']}: {ticket['title']}")
        success = zammad.delete_ticket(ticket['id'])
        if success:
          deleted_count += 1
        else:
          logger.error(f"Failed to delete ticket {ticket['id']}")
      except Exception as e:
        logger.error(f"Error deleting ticket {ticket['id']}: {str(e)}")

    # Format the result message
    if deleted_count == len(matching_tickets):
      result.message = f"Successfully deleted all {deleted_count} tickets with subject containing '{subject}'."
    else:
      result.message = f"Deleted {deleted_count} of {len(matching_tickets)} tickets with subject containing '{subject}'."

    return result
