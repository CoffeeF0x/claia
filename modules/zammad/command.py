"""
Zammad integration module command implementation for Claia.

This module provides commands for interacting with the Zammad ticketing system.
"""

# External dependencies
import logging
import os
from typing import Optional

# Internal dependencies
from commands.base import Command, command
from settings import Settings
from results import Result

# Internal dependencies
from models import run as model_run
from files import Conversation
from enums import MessageRole
from .settings import ZammadSettings
from .api import ZammadAPI
from .constants import ACCOUNT_MANAGEMENT_PROMPT, VERIFICATION_PROMPT
from .utils import require_zammad_config, zammad_run_process



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
  def list_tickets(self, settings: Settings, query: str = "open-tickets") -> Result:
    """
    List tickets from Zammad based on a query.

    Args:
      settings: Application settings
      query: Query name or custom query string

    Returns:
      Result: Operation result
    """
    # Create result
    result = Result()

    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.status = "error"
      return result

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    logger.debug("Listing tickets with query: %s", query)

    # Get tickets
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
  def get_ticket_details(self, settings: Settings, ticket_id: str) -> Result:
    """
    Get details of a specific ticket from Zammad.

    Args:
      settings: Application settings
      ticket_id: The ID of the ticket to retrieve

    Returns:
      Result: Operation result with ticket details
    """
    # Create result
    result = Result()

    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.status = "error"
      return result

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

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
  def add_tag(self, settings: Settings, ticket_id: str, tag: str) -> Result:
    """
    Add a tag to a ticket in Zammad.

    Args:
      settings: Application settings
      ticket_id: The ID of the ticket to tag
      tag: The tag to add to the ticket

    Returns:
      Result: Operation result
    """
    # Create result
    result = Result()

    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.status = "error"
      return result

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    logger.debug("Adding tag '%s' to ticket %s", tag, ticket_id)

    tag_result = zammad.add_tag(int(ticket_id), tag)

    if tag_result:
      logger.info("Successfully added tag '%s' to ticket %s", tag, ticket_id)
      result.message = f"Successfully added tag '{tag}' to ticket {ticket_id}."
    else:
      logger.error("Failed to add tag '%s' to ticket %s", tag, ticket_id)
      result.message = f"Failed to add tag '{tag}' to ticket {ticket_id}."
      result.status = "error"

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
  def remove_tag(self, settings: Settings, ticket_id: str, tag: str) -> Result:
    """
    Remove a tag from a ticket in Zammad.

    Args:
      settings: Application settings
      ticket_id: The ID of the ticket
      tag: The tag to remove from the ticket

    Returns:
      Result: Operation result
    """
    # Create result
    result = Result()

    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.status = "error"
      return result

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    logger.debug("Removing tag '%s' from ticket %s", tag, ticket_id)

    tag_result = zammad.remove_tag(int(ticket_id), tag)

    if tag_result:
      logger.info("Successfully removed tag '%s' from ticket %s", tag, ticket_id)
      result.message = f"Successfully removed tag '{tag}' from ticket {ticket_id}."
    else:
      logger.error("Failed to remove tag '%s' from ticket %s", tag, ticket_id)
      result.message = f"Failed to remove tag '{tag}' from ticket {ticket_id}."
      result.status = "error"

    return result

  @command(
    path=["process"],
    description="Process untagged tickets",
    help_text="Process untagged tickets and add AI tags",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  def process_tickets(self, settings: Settings) -> Result:
    """
    Process untagged tickets and add AI tags.

    Args:
      settings: Application settings

    Returns:
      Result: Processing result
    """
    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result = Result()
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.status = "error"
      return result

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    logger.debug("Starting ticket processing command")
    # Process tickets
    result = zammad_run_process(settings, zammad)
    logger.info("Ticket processing completed")

    if not result.message:
      result.message = "Ticket processing completed."

    return result

  @command(
    path=["untag"],
    description="Remove AI tags from tickets",
    help_text="Remove AI tags from all tagged tickets",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Untagging result"
    },
    ai_callable=True
  )
  def untag_tickets(self, settings: Settings) -> Result:
    """
    Remove AI tags from all tagged tickets.

    Args:
      settings: Application settings

    Returns:
      Result: Untagging result
    """

    logger.debug("Starting untag process for all tagged tickets")
    result = Result()

    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.status = "error"
      return result

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Get tagged tickets
    tickets = zammad.list_tickets("tagged-tickets")

    if not tickets:
      logger.info("No tagged tickets found")
      result.message = "No tagged tickets found"
      return result

    removed_count = 0
    logger.debug("Found %d tagged tickets to process", len(tickets))

    # Remove AI tags from each ticket
    for ticket_id in tickets:
      logger.debug("Processing ticket %s", ticket_id)
      tags = zammad.list_tags(ticket_id)
      ai_tags = [tag for tag in tags if tag.startswith("AI-")]
      logger.debug("Found %d AI tags for ticket %s", len(ai_tags), ticket_id)

      if ai_tags:
        for tag in ai_tags:
          if zammad.remove_tag(ticket_id, tag):
            removed_count += 1

    logger.info("Removed %d AI tags from %d tickets", removed_count, len(tickets))
    result.message = f"Completed! Removed {removed_count} AI tags from {len(tickets)} tickets"
    return result

  @command(
    path=["account-management"],
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
        }
      }
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  def process_account_tickets(self, settings: Settings, output_file: str = "account_list.txt", limit: int = 50) -> Result:
    """
    Process tickets with account management tags and build a list of accounts that need work.

    Args:
      settings: Application settings
      output_file: File to save the account list to
      limit: Maximum number of tickets to process

    Returns:
      Result: Processing result
    """
    result = Result()

    # Get Zammad settings
    zammad_settings = ZammadSettings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      result.message = f"Zammad is not properly configured. Please set TOKEN_ZAMMAD and ZAMMAD_BASEURL environment variables."
      result.status = "error"
      return result

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

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

    # Initialize or load the account list file
    file_id = None
    current_account_list = ""

    if os.path.exists(output_file):
      print(f"Loading existing account list from {output_file}")
      file_id = conversation.add_file(output_file)
      account_file = conversation.get_file(file_id)
      if account_file and hasattr(account_file, 'get_preview'):
        current_account_list = account_file.get_preview()
    else:
      print(f"Creating new account list file: {output_file}")
      # Create an empty file
      with open(output_file, "w") as f:
        f.write("")
      file_id = conversation.add_file(output_file)

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

      # Get ticket details
      ticket_details = zammad.get_ticket_details(ticket_id)

      # Prepare optimized messages for the LLM
      # For retry attempts, use a stronger prompt about preserving data
      is_retry = retry_count[ticket_id] > 1
      retry_instruction = "\n\nIMPORTANT: Previous processing of this ticket resulted in data loss. Make sure to preserve ALL existing information while adding new data from this ticket." if is_retry else ""

      account_messages = [
        {"role": "system", "content": ACCOUNT_MANAGEMENT_PROMPT + retry_instruction},
        {"role": "user", "content": f"Current account list:\n{current_account_list}\n\n\nNew ticket to process:\n{ticket_details}"}
      ]

      # Run the AI model to update the account list
      print(f"Sending ticket to LLM for processing...")
      model_result = model_run(settings.active_model, account_messages, settings=settings)

      if model_result.is_error():
        print(f"❌ Error processing ticket {ticket_id}: {model_result.get_message()}")
        # Add ticket back to the end of the queue for retry
        if retry_count[ticket_id] < max_retries:
          remaining_tickets.append(ticket_id)
          print(f"Added ticket {ticket_id} back to queue for retry later")
        continue

      # Update account list with model's response
      if model_result.data:
        print("✓ Successfully processed ticket")
        previous_account_list = current_account_list
        current_account_list = model_result.data.strip()

        # Verify no data has been lost in the update
        if previous_account_list:
          print("Verifying that no data has been lost...")
          verification_messages = [
            {"role": "system", "content": VERIFICATION_PROMPT},
            {"role": "user", "content": f"Previous list:\n{previous_account_list}\n\nUpdated list:\n{current_account_list}\n\nHas any data been lost? Respond with YES or NO followed by details."}
          ]

          verification_result = model_run(settings.active_model, verification_messages, settings=settings)

          if verification_result.is_error():
            print(f"⚠️ Error during verification: {verification_result.get_message()}")
            # Add ticket back to the end of the queue for retry
            if retry_count[ticket_id] < max_retries:
              remaining_tickets.append(ticket_id)
              print(f"Added ticket {ticket_id} back to queue for retry later (verification error)")
            continue

          verification_response = verification_result.data.strip()
          if verification_response.startswith("YES"):
            print("⚠️ WARNING: Possible data loss detected!")
            print(f"Details: {verification_response}")
            print("Reverting to previous account list...")
            current_account_list = previous_account_list

            # Add ticket back to the end of the queue for retry
            if retry_count[ticket_id] < max_retries:
              remaining_tickets.append(ticket_id)
              print(f"Added ticket {ticket_id} back to queue for retry later (data loss detected)")
            continue
          else:
            print("✅ Verification passed: No data has been lost")
            # Ticket processed successfully

        # Get the file object and update its content
        account_file = conversation.get_file(file_id)
        if account_file and hasattr(account_file, 'get_preview'):
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

          successful_count += 1

      processed_count += 1

      # Print status information
      print(f"Processed ticket: {ticket_id}")
      print(f"Remaining tickets: {len(remaining_tickets)}")
      print(f"Current list size: {len(current_account_list)} characters")
      print(f"{'-'*50}\n")

      # Save the conversation state
      conversation.save()

    print(f"\n{'='*50}")
    print(f"Processing complete! Successfully processed {successful_count}/{len(tickets)} tickets.")
    print(f"Account list saved to {output_file}")
    print(f"{'='*50}\n")

    result.message = f"Processed {successful_count} tickets. Account list saved to {output_file}"
    return result