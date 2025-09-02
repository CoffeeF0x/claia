"""
Zammad integration module for CLAIA.

This module provides commands for interacting with the Zammad ticketing system.
"""

# External dependencies
import logging
import pluggy
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Internal dependencies (absolute imports aligned with project structure)
from claia.hooks.module import CommandModuleInfo, CommandDefinition, ArgumentDefinition


########################################################################
#                            INITIALIZATION                            #
########################################################################
hookimpl = pluggy.HookimplMarker("claia_command_modules")
logger = logging.getLogger(__name__)


########################################################################
#                              CONSTANTS                               #
########################################################################
# Available tags list
TAG_LIST = [
  "Phishing",
  "Spam",
  "Completed",
  "NetworkHardware",
  "Jenzabar",
  "LMS",
  "Report",
  "Printers",
  "Forms",
  "Adobe",
  "InfoMaker",
  "Salesforce",
  "Classroom",
  "Login",
  "Student",
  "Filter",
  "Video",
  "AccountManagement",
  "NoCategoryFound"
]

# Predefined ticket queries
TICKET_QUERIES: Dict[str, str] = {
  "new-tickets"       : "state_id:1",
  "open-tickets"      : "state_id:1 OR state_id:2 OR state_id:3",
  "reminder-tickets"  : "state_id:3",
  "untagged-tickets"  : "(state_id:1 OR state_id:2 OR state_id:3) AND !(tags:AI-Tagged)",
  "tagged-tickets"    : "tags:AI-Tagged",
  "high-priority"     : "priority.name:\"3 high\"",
  "account-management": "(tags:\"AD & User Account Management\" OR tags:AI-AccountManagement) AND (state_id:1 OR state_id:2 OR state_id:3)"
}

# Safety limit for pagination
SAFETY_LIMIT = 500


########################################################################
#                             ZAMMAD API                               #
########################################################################
try:
  from aia import AIASession
except ImportError:  # pragma: no cover - optional dependency fallback
  class AIASession:
    def cadata_from_url(self, url):
      return ""

import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
from tempfile import NamedTemporaryFile


class ZammadAPI:
  """Simple client for interacting with the Zammad API."""

  def __init__(self, base_url: str, api_token: str) -> None:
    logger.debug(f"Initializing ZammadAPI with base_url: {base_url}")
    self.base_url = base_url
    self.api_token = api_token
    self.headers = {
      "Authorization": f"Token token={self.api_token}",
      "Content-Type": "application/json"
    }
    self.session = AIASession()

  def _make_request(self, method: str, endpoint: str, data=None):
    url = f"{self.base_url}{endpoint}"
    cadata = self.session.cadata_from_url(url)
    with NamedTemporaryFile("w") as pem_file:
      pem_file.write(cadata)
      pem_file.flush()
      if method.lower() == 'get':
        response = requests.get(url, headers=self.headers, verify=pem_file.name)
      elif method.lower() == 'post':
        response = requests.post(url, headers=self.headers, json=data, verify=pem_file.name)
      elif method.lower() == 'delete':
        response = requests.delete(url, headers=self.headers, json=data, verify=pem_file.name)
      else:
        raise ValueError(f"Unsupported HTTP method: {method}")
      response.raise_for_status()
      return response.json() if response.content else None

  def get(self, endpoint: str):
    return self._make_request('get', endpoint)

  def post(self, endpoint: str, data: dict):
    return self._make_request('post', endpoint, data)

  def delete(self, endpoint: str, data: dict):
    return self._make_request('delete', endpoint, data)

  def _clean_html_content(self, text: str) -> str:
    if not text:
      return ""
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text(separator='\n')
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text.strip())
    return clean_text

  def _extract_unique_content(self, articles: List[dict]) -> List[dict]:
    seen_content = set()
    unique_articles = []
    for article in articles:
      clean_body = self._clean_html_content(article.get('body', ''))
      paragraphs = clean_body.split('\n\n')
      unique_paragraphs = []
      for para in paragraphs:
        normalized_para = re.sub(r'\s+', ' ', para.strip())
        if len(normalized_para) > 30 and normalized_para not in seen_content:
          seen_content.add(normalized_para)
          unique_paragraphs.append(para)
      if unique_paragraphs:
        new_article = article.copy()
        new_article['body'] = '\n\n'.join(unique_paragraphs)
        unique_articles.append(new_article)
    return unique_articles

  def list_tickets(self, query_name: str = "open-tickets", limit: int = 100, full_response: bool = False):
    query = TICKET_QUERIES.get(query_name, query_name)
    encoded_query = urllib.parse.quote(query)
    try:
      page = 1
      response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
      ticket_ids = response["tickets"]
      assets = response["assets"]
      ticket_count = response["tickets_count"]
      tickets: List[dict] = []
      while full_response and response["tickets_count"] > 0 and page * limit < SAFETY_LIMIT:
        page += 1
        response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
        ticket_ids.extend(response["tickets"])
        assets.extend(response["assets"])
        ticket_count += response["tickets_count"]
      for ticket in assets["Ticket"].values():
        tickets.append(ticket)
      return tickets
    except Exception as e:  # pragma: no cover - network errors
      logger.error(f"Error listing tickets: {str(e)}")
      return None

  def get_ticket_details(self, ticket_id: str, compact: bool = False) -> str:
    try:
      ticket = self.get(f"tickets/{ticket_id}")
      articles = self.get(f"ticket_articles/by_ticket/{ticket_id}")
      unique_articles = self._extract_unique_content(articles or [])
      width = 78
      response: List[str] = [f"┌{'─' * width}┐"]
      response.append(f"│ {'TICKET DETAILS':^{width-2}} │")
      response.append(f"├{'─' * width}┤")
      response.append(f"│ {'Ticket ID:':<15} {ticket['id']:<{width-18}} │")
      response.append(f"│ {'Number:':<15} {ticket.get('number', ''):<{width-18}} │")
      response.append(f"│ {'Title:':<15} {ticket.get('title', ''):<{width-18}} │")
      response.append(f"│ {'State:':<15} {ticket.get('state', str(ticket.get('state_id', ''))):<{width-18}} │")
      response.append(f"│ {'Priority:':<15} {ticket.get('priority', str(ticket.get('priority_id', ''))):<{width-18}} │")
      response.append(f"│ {'Created At:':<15} {ticket.get('created_at', ''):<{width-18}} │")
      response.append(f"│ {'Updated At:':<15} {ticket.get('updated_at', ''):<{width-18}} │")
      tags = ticket.get('tags', [])
      if tags:
        response.append(f"│ {'Tags:':<15} {', '.join(tags):<{width-18}} │")
      response.append(f"├{'─' * width}┤")
      response.append(f"│ {'CONVERSATION HISTORY':^{width-2}} │")
      response.append(f"├{'─' * width}┤")
      if not unique_articles:
        response.append(f"│ {'No conversation history found':^{width-2}} │")
        response.append(f"└{'─' * width}┘")
        return "\n".join(response)
      for i, article in enumerate(unique_articles):
        response.append(f"│ {'Message #' + str(i+1):^{width-2}} │")
        response.append(f"├{'─' * width}┤")
        response.append(f"│ {'From:':<10} {article.get('from', 'Unknown'):<{width-13}} │")
        if article.get('to'):
          response.append(f"│ {'To:':<10} {article.get('to', ''):<{width-13}} │")
        if article.get('cc'):
          response.append(f"│ {'CC:':<10} {article.get('cc', ''):<{width-13}} │")
        response.append(f"│ {'Subject:':<10} {article.get('subject', ''):<{width-13}} │")
        response.append(f"│ {'Date:':<10} {article.get('created_at', ''):<{width-13}} │")
        response.append(f"├{'─' * width}┤")
        body = article.get('body', '')
        if compact:
          if body:
            preview = body.replace('\n', ' ').strip()[:100]
            if len(body) > 100:
              preview += '...'
            response.append(f"│ {preview:<{width-2}} │")
        else:
          if body:
            lines: List[str] = []
            for line in body.split('\n'):
              while line and len(line) > width-4:
                break_point = line[:width-4].rfind(' ')
                if break_point == -1 or break_point < 30:
                  break_point = width-4
                lines.append(line[:break_point])
                line = line[break_point:].lstrip()
              if line:
                lines.append(line)
            for line in lines:
              response.append(f"│ {line:<{width-2}} │")
          else:
            response.append(f"│ {'(No content)':<{width-2}} │")
        if i < len(unique_articles) - 1:
          response.append(f"├{'─' * width}┤")
        else:
          response.append(f"└{'─' * width}┘")
      if compact:
        response.append("\nTo view full message bodies:")
        response.append(f"claia zammad details {ticket_id}")
      else:
        response.append("\nFor a more compact view:")
        response.append(f"claia zammad details {ticket_id} --compact")
      return "\n".join(response)
    except Exception as e:  # pragma: no cover - network errors
      logger.error(f"Error getting ticket details: {str(e)}")
      return f"Error getting ticket details: {str(e)}"

  def list_tags(self, ticket_id: int) -> List[str]:
    try:
      response = self.get(f"tags?object=Ticket&o_id={ticket_id}")
      return response.get("tags", []) if isinstance(response, dict) else []
    except Exception as e:  # pragma: no cover
      logger.error(f"Error listing tags for ticket {ticket_id}: {str(e)}")
      return []

  def add_tag(self, ticket_id: int, tag: str) -> bool:
    data = {"item": tag, "object": "Ticket", "o_id": ticket_id}
    try:
      self.post("tags/add", data)
      return True
    except Exception as e:  # pragma: no cover
      logger.error(f"Error adding tag '{tag}' to ticket {ticket_id}: {str(e)}")
      return False

  def remove_tag(self, ticket_id: int, tag: str) -> bool:
    data = {"item": tag, "object": "Ticket", "o_id": ticket_id}
    try:
      self.delete("tags/remove", data)
      return True
    except Exception as e:  # pragma: no cover
      logger.error(f"Error removing tag '{tag}' from ticket {ticket_id}: {str(e)}")
      return False

  def delete_ticket(self, ticket_id: int) -> bool:
    try:
      self.delete(f"tickets/{ticket_id}", {})
      return True
    except Exception as e:  # pragma: no cover
      logger.error(f"Error deleting ticket with ID {ticket_id}: {str(e)}")
      return False


########################################################################
#                               HELPERS                                #
########################################################################
def untag_ticket(zammad: ZammadAPI, ticket_id: int) -> Tuple[int, List[str]]:
  """Remove AI-* tags from a single ticket."""
  tags = zammad.list_tags(ticket_id)
  ai_tags = [t for t in tags if isinstance(t, str) and t.startswith("AI-")]
  removed: List[str] = []
  for tag in ai_tags:
    if zammad.remove_tag(ticket_id, tag):
      removed.append(tag)
  return len(removed), removed


def find_tickets_by_subject(zammad: ZammadAPI, subject: str, limit: int = 0) -> List[Dict[str, Any]]:
  """Find tickets whose title contains subject (case-insensitive)."""
  all_tickets = zammad.list_tickets("open-tickets", limit=999, full_response=True) or []
  matches: List[Dict[str, Any]] = []
  for ticket in all_tickets:
    title = ticket.get('title', '')
    if isinstance(title, str) and subject.lower() in title.lower():
      matches.append({
        'id': ticket.get('id'),
        'title': title,
        'created_at': ticket.get('created_at', 'Unknown'),
        'customer': ticket.get('customer', 'Unknown')
      })
      if limit > 0 and len(matches) >= limit:
        break
  return matches

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
      details = zammad.get_ticket_details(ticket_id)
      return details if details else f"Ticket {ticket_id} not found."

    except Exception as e:
      logger.exception(f"Error getting ticket details: {str(e)}")
      return f"Error getting ticket details: {str(e)}"

  def _add_tag(self, ticket_id: int, tag: str, **kwargs) -> str:
    """Add a tag to a ticket."""
    try:
      zammad = self._get_zammad_api()
      if zammad.add_tag(ticket_id, tag):
        return f"Successfully added tag '{tag}' to ticket {ticket_id}."
      return f"Failed to add tag '{tag}' to ticket {ticket_id}."

    except Exception as e:
      logger.exception(f"Error adding tag: {str(e)}")
      return f"Error adding tag: {str(e)}"

  def _remove_tag(self, ticket_id: int, tag: str, **kwargs) -> str:
    """Remove a tag from a ticket."""
    try:
      zammad = self._get_zammad_api()
      if zammad.remove_tag(ticket_id, tag):
        return f"Successfully removed tag '{tag}' from ticket {ticket_id}."
      return f"Failed to remove tag '{tag}' from ticket {ticket_id}."

    except Exception as e:
      logger.exception(f"Error removing tag: {str(e)}")
      return f"Error removing tag: {str(e)}"

  def _process_single_ticket(self, ticket_id: int, **kwargs) -> str:
    """Process a single ticket and add AI tags."""
    try:
      # Simplified for new architecture - AI tagging pipeline not included here
      return "Not implemented: AI-based tagging is handled by model pipeline."

    except Exception as e:
      logger.exception(f"Error processing ticket: {str(e)}")
      return f"Error processing ticket: {str(e)}"

  def _untag_single_ticket(self, ticket_id: int, **kwargs) -> str:
    """Remove AI tags from a single ticket."""
    try:
      zammad = self._get_zammad_api()
      count, tags = untag_ticket(zammad, ticket_id)
      if count > 0:
        return f"Removed {count} AI tags from ticket {ticket_id}: {', '.join(tags)}"
      return f"No AI tags found on ticket {ticket_id}."

    except Exception as e:
      logger.exception(f"Error untagging ticket: {str(e)}")
      return f"Error untagging ticket: {str(e)}"

  def _process_account_single(self, ticket_id: int, **kwargs) -> str:
    """Process a single account management ticket."""
    try:
      return "Not implemented: account processing requires AI model orchestration."

    except Exception as e:
      logger.exception(f"Error processing account ticket: {str(e)}")
      return f"Error processing account ticket: {str(e)}"

  def _process_tag_tickets(self, limit: int = 0, **kwargs) -> str:
    """Process untagged tickets and add AI tags."""
    try:
      # Simplified: this operation depends on AI tagging, which is outside this module now
      return "Not implemented: use model pipeline to tag tickets."

    except Exception as e:
      logger.exception(f"Error processing tickets: {str(e)}")
      return f"Error processing tickets: {str(e)}"

  def _process_untag_tickets(self, limit: int = 0, **kwargs) -> str:
    """Remove AI tags from all tagged tickets."""
    try:
      zammad = self._get_zammad_api()
      tickets = zammad.list_tickets("tagged-tickets") or []
      if not tickets:
        return "No AI-tagged tickets found."
      if limit > 0:
        tickets = tickets[:limit]
      processed = 0
      for ticket in tickets:
        untag_ticket(zammad, ticket.get('id'))
        processed += 1
      return f"Removed AI tags from {processed} tickets."

    except Exception as e:
      logger.exception(f"Error untagging tickets: {str(e)}")
      return f"Error untagging tickets: {str(e)}"

  def _process_account_tickets(self, output_file: str = "account-list.txt", limit: int = 0, **kwargs) -> str:
    """Process account management tickets and build account list."""
    try:
      return "Not implemented: account processing requires AI model orchestration."

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
