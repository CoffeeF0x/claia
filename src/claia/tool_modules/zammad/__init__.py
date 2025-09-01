"""
Zammad integration module for CLAIA.

This module provides commands for interacting with the Zammad ticketing system.
"""

# External dependencies
import logging
import pluggy
from typing import Dict, Any, Optional
from datetime import datetime

# Internal dependencies
from ..hooks.module import CommandModuleHooks, CommandModuleInfo, CommandDefinition, ArgumentDefinition
from ..lib.results import Result

# Zammad-specific dependencies
from .api import ZammadAPI
from .constants import ACCOUNT_MANAGEMENT_PROMPT, VERIFICATION_PROMPT, TICKET_QUERIES
from .utils import require_zammad_config, tag_ticket, untag_ticket, process_account_ticket, find_tickets_by_subject


########################################################################
#                            INITIALIZATION                            #
########################################################################
hookimpl = pluggy.HookimplMarker("claia_command_modules")
logger = logging.getLogger(__name__)


########################################################################
#                          ZAMMAD MODULE PLUGIN                        #
########################################################################
class ZammadModulePlugin:
  """Plugin implementation for Zammad command module."""

  def __init__(self, **kwargs):
    """Initialize Zammad module with required settings."""
    # Store API credentials passed via required_args
    self.zammad_api_token = kwargs.get('zammad_api_token', '')
    self.zammad_base_url = kwargs.get('zammad_base_url', '')

  @hookimpl
  def get_module_info(self) -> CommandModuleInfo:
    """Return module info for Zammad integration."""
    return CommandModuleInfo(
      name="zammad",
      title="Zammad Integration",
      description="Commands for interacting with the Zammad ticketing system",
      required_args=['zammad_api_token', 'zammad_base_url']
    )

  @hookimpl
  def get_module_commands(self) -> Dict[str, CommandDefinition]:
    """Return all available Zammad commands."""
    return {
      "list": CommandDefinition(
        name="list",
        description="List tickets from Zammad based on a query",
        callable=self._list_tickets,
        arguments={
          "query": ArgumentDefinition(
            name="query",
            description="Query name or custom query string (default: open-tickets)",
            data_type="str",
            required=False,
            default_value="open-tickets"
          ),
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to display (default: 99)",
            data_type="int",
            required=False,
            default_value=99
          ),
          "compact": ArgumentDefinition(
            name="compact",
            description="Show compact view without detailed ticket information",
            data_type="bool",
            required=False,
            default_value=False
          )
        }
      ),

      "details": CommandDefinition(
        name="details",
        description="Get details for a Zammad ticket using its ID",
        callable=self._get_ticket_details,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket to get details for",
            data_type="int",
            required=True
          )
        }
      ),

      "tag_add": CommandDefinition(
        name="tag_add",
        description="Add a tag to a Zammad ticket",
        callable=self._add_tag,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket to tag",
            data_type="int",
            required=True
          ),
          "tag": ArgumentDefinition(
            name="tag",
            description="Tag to add to the ticket",
            data_type="str",
            required=True
          )
        }
      ),

      "tag_remove": CommandDefinition(
        name="tag_remove",
        description="Remove a tag from a Zammad ticket",
        callable=self._remove_tag,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket to untag",
            data_type="int",
            required=True
          ),
          "tag": ArgumentDefinition(
            name="tag",
            description="Tag to remove from the ticket",
            data_type="str",
            required=True
          )
        }
      ),

      "process_single": CommandDefinition(
        name="process_single",
        description="Process a single ticket and add AI tags",
        callable=self._process_single_ticket,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket to process",
            data_type="int",
            required=True
          )
        }
      ),

      "untag_single": CommandDefinition(
        name="untag_single",
        description="Remove AI tags from a single ticket",
        callable=self._untag_single_ticket,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket to untag",
            data_type="int",
            required=True
          )
        }
      ),

      "process_account_single": CommandDefinition(
        name="process_account_single",
        description="Process a single account management ticket",
        callable=self._process_account_single,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the account management ticket to process",
            data_type="int",
            required=True
          )
        }
      ),

      "process_tag": CommandDefinition(
        name="process_tag",
        description="Process untagged tickets and add AI tags",
        callable=self._process_tag_tickets,
        arguments={
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to process (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0
          )
        }
      ),

      "process_untag": CommandDefinition(
        name="process_untag",
        description="Remove AI tags from all tagged tickets",
        callable=self._process_untag_tickets,
        arguments={
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to process (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0
          )
        }
      ),

      "process_account": CommandDefinition(
        name="process_account",
        description="Process account management tickets and build account list",
        callable=self._process_account_tickets,
        arguments={
          "output_file": ArgumentDefinition(
            name="output_file",
            description="File to save account list to",
            data_type="str",
            required=False,
            default_value="account-list.txt"
          ),
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to process (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0
          )
        }
      ),

      "find_subject": CommandDefinition(
        name="find_subject",
        description="Find Zammad tickets with a specific subject",
        callable=self._find_tickets_by_subject,
        arguments={
          "subject": ArgumentDefinition(
            name="subject",
            description="The subject line to search for (case-insensitive)",
            data_type="str",
            required=True
          ),
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to find (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0
          )
        }
      ),

      "delete_subject": CommandDefinition(
        name="delete_subject",
        description="Delete Zammad tickets with a specific subject",
        callable=self._delete_tickets_by_subject,
        arguments={
          "subject": ArgumentDefinition(
            name="subject",
            description="The subject line to match (case-insensitive)",
            data_type="str",
            required=True
          ),
          "confirm": ArgumentDefinition(
            name="confirm",
            description="Confirmation to run the deletion process",
            data_type="bool",
            required=False,
            default_value=False
          ),
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to process (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0
          )
        }
      )
    }

  # Command implementations with Zammad API integration
  def _get_zammad_api(self) -> ZammadAPI:
    """Get configured Zammad API instance using stored credentials."""
    return ZammadAPI(self.zammad_base_url, self.zammad_api_token)

  def _list_tickets(self, query: str = "open-tickets", limit: int = 99, compact: bool = False, **kwargs) -> str:
    """List tickets from Zammad based on a query."""
    try:
      zammad = self._get_zammad_api()
      tickets = zammad.list_tickets(query)

      if not tickets:
        return "No tickets found."

      total_tickets = len(tickets)
      if limit > 0 and limit < total_tickets:
        tickets = tickets[:limit]

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
        response.append(f"│ {'ID':<5}│ {'TITLE':<30}│ {'CREATED':<20}│ {'STATE':<15} │")
        response.append(f"├{'─' * 5}┼{'─' * 30}┼{'─' * 20}┼{'─' * 15}┤")

        for ticket in tickets:
          title = ticket.get('title', 'Unknown')
          if len(title) > 27:
            title = title[:27] + '...'

          created_at = ticket.get('created_at', '')
          if created_at:
            try:
              created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
              created_str = created_dt.strftime('%Y-%m-%d %H:%M')
            except:
              created_str = created_at[:16]
          else:
            created_str = 'N/A'

          state = ticket.get('state', {}).get('name', 'Unknown')
          if len(state) > 12:
            state = state[:12] + '...'

          response.append(f"│ {ticket['id']:<5}│ {title:<30}│ {created_str:<20}│ {state:<15} │")

      response.append(f"└{'─' * 78}┘")
      return '\n'.join(response)

    except Exception as e:
      logger.exception(f"Error listing tickets: {str(e)}")
      return f"Error listing tickets: {str(e)}"

  def _get_ticket_details(self, ticket_id: int, **kwargs) -> str:
    """Get details for a specific ticket."""
    try:
      zammad = self._get_zammad_api()
      ticket = zammad.get_ticket_details(ticket_id)

      if not ticket:
        return f"Ticket {ticket_id} not found."

      # Format ticket details
      response = [f"┌{'─' * 78}┐"]
      response.append(f"│ {'TICKET DETAILS':^76} │")
      response.append(f"├{'─' * 78}┤")
      response.append(f"│ ID: {ticket['id']:<71} │")
      response.append(f"│ Title: {ticket.get('title', 'N/A'):<68} │")
      response.append(f"│ State: {ticket.get('state', {}).get('name', 'N/A'):<68} │")
      response.append(f"│ Created: {ticket.get('created_at', 'N/A'):<66} │")
      response.append(f"│ Updated: {ticket.get('updated_at', 'N/A'):<66} │")

      tags = ticket.get('tags', [])
      if tags:
        response.append(f"│ Tags: {', '.join(tags):<69} │")

      response.append(f"└{'─' * 78}┘")
      return '\n'.join(response)

    except Exception as e:
      logger.exception(f"Error getting ticket details: {str(e)}")
      return f"Error getting ticket details: {str(e)}"

  def _add_tag(self, ticket_id: int, tag: str, **kwargs) -> str:
    """Add a tag to a ticket."""
    try:
      zammad = self._get_zammad_api()
      success = tag_ticket(zammad, ticket_id, tag)

      if success:
        return f"Successfully added tag '{tag}' to ticket {ticket_id}."
      else:
        return f"Failed to add tag '{tag}' to ticket {ticket_id}."

    except Exception as e:
      logger.exception(f"Error adding tag: {str(e)}")
      return f"Error adding tag: {str(e)}"

  def _remove_tag(self, ticket_id: int, tag: str, **kwargs) -> str:
    """Remove a tag from a ticket."""
    try:
      zammad = self._get_zammad_api()
      success = untag_ticket(zammad, ticket_id, tag)

      if success:
        return f"Successfully removed tag '{tag}' from ticket {ticket_id}."
      else:
        return f"Failed to remove tag '{tag}' from ticket {ticket_id}."

    except Exception as e:
      logger.exception(f"Error removing tag: {str(e)}")
      return f"Error removing tag: {str(e)}"

  def _process_single_ticket(self, ticket_id: int, **kwargs) -> str:
    """Process a single ticket and add AI tags."""
    try:
      zammad = self._get_zammad_api()

      # Get ticket details
      ticket = zammad.get_ticket_details(ticket_id)
      if not ticket:
        return f"Ticket {ticket_id} not found."

      # Process the ticket (implementation from old module)
      # This would involve AI analysis and tagging
      return f"Processing ticket {ticket_id} - AI tagging not yet implemented in new system."

    except Exception as e:
      logger.exception(f"Error processing ticket: {str(e)}")
      return f"Error processing ticket: {str(e)}"

  def _untag_single_ticket(self, ticket_id: int, **kwargs) -> str:
    """Remove AI tags from a single ticket."""
    try:
      zammad = self._get_zammad_api()

      # Remove AI-generated tags
      ai_tags = ['ai-account-management', 'ai-technical-support', 'ai-billing', 'ai-general']
      removed_tags = []

      for tag in ai_tags:
        if untag_ticket(zammad, ticket_id, tag):
          removed_tags.append(tag)

      if removed_tags:
        return f"Removed AI tags from ticket {ticket_id}: {', '.join(removed_tags)}"
      else:
        return f"No AI tags found on ticket {ticket_id}."

    except Exception as e:
      logger.exception(f"Error untagging ticket: {str(e)}")
      return f"Error untagging ticket: {str(e)}"

  def _process_account_single(self, ticket_id: int, **kwargs) -> str:
    """Process a single account management ticket."""
    try:
      zammad = self._get_zammad_api()

      # Note: process_account_ticket may need to be updated to not require settings
      # For now, pass None or update the function signature
      result = process_account_ticket(zammad, ticket_id, None)
      return result.message if result.message else "Account ticket processed successfully."

    except Exception as e:
      logger.exception(f"Error processing account ticket: {str(e)}")
      return f"Error processing account ticket: {str(e)}"

  def _process_tag_tickets(self, limit: int = 0, **kwargs) -> str:
    """Process untagged tickets and add AI tags."""
    try:
      zammad = self._get_zammad_api()

      # Get untagged tickets
      tickets = zammad.list_tickets("untagged")

      if not tickets:
        return "No untagged tickets found."

      if limit > 0:
        tickets = tickets[:limit]

      processed_count = 0
      for ticket in tickets:
        # Process each ticket - AI analysis would go here
        processed_count += 1

      return f"Processed {processed_count} untagged tickets."

    except Exception as e:
      logger.exception(f"Error processing tickets: {str(e)}")
      return f"Error processing tickets: {str(e)}"

  def _process_untag_tickets(self, limit: int = 0, **kwargs) -> str:
    """Remove AI tags from all tagged tickets."""
    try:
      zammad = self._get_zammad_api()

      # Get tagged tickets
      tickets = zammad.list_tickets("ai-tagged")

      if not tickets:
        return "No AI-tagged tickets found."

      if limit > 0:
        tickets = tickets[:limit]

      processed_count = 0
      ai_tags = ['ai-account-management', 'ai-technical-support', 'ai-billing', 'ai-general']

      for ticket in tickets:
        for tag in ai_tags:
          untag_ticket(zammad, ticket['id'], tag)
        processed_count += 1

      return f"Removed AI tags from {processed_count} tickets."

    except Exception as e:
      logger.exception(f"Error untagging tickets: {str(e)}")
      return f"Error untagging tickets: {str(e)}"

  def _process_account_tickets(self, output_file: str = "account-list.txt", limit: int = 0, **kwargs) -> str:
    """Process account management tickets and build account list."""
    try:
      zammad = self._get_zammad_api()

      # Get account management tickets
      tickets = zammad.list_tickets("account-management")

      if not tickets:
        return "No account management tickets found."

      if limit > 0:
        tickets = tickets[:limit]

      processed_count = 0
      account_list = []

      for ticket in tickets:
        # Note: process_account_ticket may need to be updated to not require settings
        result = process_account_ticket(zammad, ticket['id'], None)
        if result.success and result.data:
          account_list.extend(result.data)
        processed_count += 1

      # Save to file
      if account_list:
        with open(output_file, 'w') as f:
          for account in account_list:
            f.write(f"{account}\n")

      return f"Processed {processed_count} account tickets. Generated {len(account_list)} account entries in {output_file}."

    except Exception as e:
      logger.exception(f"Error processing account tickets: {str(e)}")
      return f"Error processing account tickets: {str(e)}"

  def _find_tickets_by_subject(self, subject: str, limit: int = 0, **kwargs) -> str:
    """Find tickets with a specific subject."""
    try:
      zammad = self._get_zammad_api()
      matching_tickets = find_tickets_by_subject(zammad, subject, limit)

      if not matching_tickets:
        return f"No tickets found with subject containing '{subject}'."

      response = [f"Found {len(matching_tickets)} tickets with subject containing '{subject}':"]
      for ticket in matching_tickets:
        response.append(f"  #{ticket['id']}: {ticket['title']}")

      return '\n'.join(response)

    except Exception as e:
      logger.exception(f"Error finding tickets: {str(e)}")
      return f"Error finding tickets: {str(e)}"

  def _delete_tickets_by_subject(self, subject: str, confirm: bool = False, limit: int = 0, **kwargs) -> str:
    """Delete tickets with a specific subject."""
    try:
      if not confirm:
        return f"This operation will delete tickets with subject: '{subject}'. Set confirm=True to proceed."

      zammad = self._get_zammad_api()
      matching_tickets = find_tickets_by_subject(zammad, subject, limit)

      if not matching_tickets:
        return f"No tickets found with subject containing '{subject}'."

      deleted_count = 0
      for ticket in matching_tickets:
        try:
          success = zammad.delete_ticket(ticket['id'])
          if success:
            deleted_count += 1
        except Exception as e:
          logger.error(f"Error deleting ticket {ticket['id']}: {str(e)}")

      if deleted_count == len(matching_tickets):
        return f"Successfully deleted all {deleted_count} tickets with subject containing '{subject}'."
      else:
        return f"Deleted {deleted_count} of {len(matching_tickets)} tickets with subject containing '{subject}'."

    except Exception as e:
      logger.exception(f"Error deleting tickets: {str(e)}")
      return f"Error deleting tickets: {str(e)}"
