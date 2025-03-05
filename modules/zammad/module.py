"""
Zammad integration module for Claia

This module provides functionality for interacting with the Zammad ticketing system.
"""

# External dependencies
import os
import json
import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from tempfile import NamedTemporaryFile

# Internal dependencies
from commands.base import Command, command
from errors import Result
from settings import Settings


# Try to import AIA, but make it optional
try:
  from aia import AIASession
except ImportError:
  # Create a fallback class if AIA is not available
  class AIASession:
    def cadata_from_url(self, url):
      return ""



##################################################
#                  CONSTANTS                     #
##################################################
# Environment variable names
ENV_ZAMMAD_API_TOKEN = "TOKEN_ZAMMAD"
ENV_ZAMMAD_BASE_URL = "ZAMMAD_BASEURL"



##################################################
#                   SETTINGS                     #
##################################################
class ZammadSettings:
  """
  Settings for the Zammad module.

  Attributes:
    api_token (str): API token for Zammad.
    base_url (str): Base URL for Zammad API.
  """

  def __init__(self):
    self.api_token: str = ""
    self.base_url: str = ""
    self.load_from_env()

  def load_from_env(self) -> None:
    """
    Load settings from environment variables.
    """
    def strip_quotes(value: str) -> str:
      if value and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
      return value

    self.api_token = strip_quotes(os.environ.get(ENV_ZAMMAD_API_TOKEN, ""))
    self.base_url = strip_quotes(os.environ.get(ENV_ZAMMAD_BASE_URL, ""))

  def is_configured(self) -> bool:
    """
    Check if the Zammad settings are properly configured.

    Returns:
      bool: True if both API token and base URL are set, False otherwise.
    """
    return bool(self.api_token and self.base_url)


def get_settings() -> ZammadSettings:
  """
  Get the Zammad settings.

  Returns:
    ZammadSettings: The Zammad settings.
  """
  return ZammadSettings()



##################################################
#                  ZAMMAD API                    #
##################################################
class ZammadAPI:
  """Class for interacting with the Zammad API."""
  def __init__(self, base_url = str, api_token = str) -> None:
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

  def add_tag(self, ticket_id: int, tag: str):
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      response = self.post("tags/add", data)
      print(f"Successfully added tag '{tag}' to ticket {ticket_id}")
      return response
    except Exception as e:
      print(f"Error adding tag '{tag}' to ticket {ticket_id}: {str(e)}")
      return None

  def list_tickets(self, query_name: str = "open-tickets", limit: int = 100, full_response: bool = True):
    queries = {
      "new-tickets": "state_id:1",
      "open-tickets": "state_id:1 OR state_id:2 OR state_id:3",
      "reminder-tickets": "state_id:3",
      "untagged-tickets": "(state_id:1 OR state_id:2 OR state_id:3) AND !(tags:AI-Tagged)",
      "tagged-tickets": "tags:AI-Tagged",
      "high-priority": "priority.name:\"3 high\""
    }
    response = None
    tickets = None
    page = 1

    if query_name in queries:
      query = queries[query_name]
    else:
      query = query_name

    encoded_query = urllib.parse.quote(query)

    try:
      response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
      tickets = response["tickets"]
      ticket_count = response["tickets_count"]
      print(f"tickets: {ticket_count}")

      while full_response and response["tickets_count"] > 0:
        print(f"total tickets: {ticket_count}")
        page += 1
        response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
        tickets.extend(response["tickets"])
        ticket_count += response["tickets_count"]

    except Exception as e:
      print(f"Error listing tickets: {str(e)}")

    return tickets

  def _clean_html_content(self, text: str) -> str:
    if not text:
      return ""

    # First use BeautifulSoup to handle HTML properly
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text(separator='\n')

    # Remove extra whitespace and normalize newlines
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text.strip())

    return clean_text

  def _extract_unique_content(self, articles: List[dict]) -> List[dict]:
    seen_content = set()
    unique_articles = []

    for article in articles:
      # Clean the body content
      clean_body = self._clean_html_content(article['body'])

      # Split into paragraphs and process each
      paragraphs = clean_body.split('\n\n')
      unique_paragraphs = []

      for para in paragraphs:
        # Normalize the paragraph to help with matching
        normalized_para = re.sub(r'\s+', ' ', para.strip())
        if len(normalized_para) > 30:  # Only check substantial paragraphs
          if normalized_para not in seen_content:
            seen_content.add(normalized_para)
            unique_paragraphs.append(para)

      if unique_paragraphs:
        # Create a new article with only unique content
        new_article = article.copy()
        new_article['body'] = '\n\n'.join(unique_paragraphs)
        unique_articles.append(new_article)

    return unique_articles

  def get_ticket_details(self, ticket_id: str) -> None:
    response = ""

    try:
      ticket = self.get(f"tickets/{ticket_id}")
      articles = self.get(f"ticket_articles/by_ticket/{ticket_id}")

      # Process articles to remove duplicates
      unique_articles = self._extract_unique_content(articles)

      response += "Ticket Details:"
      response += f"\nTicket ID: {ticket['id']}"
      response += f"\nNumber: {ticket['number']}"
      response += f"\nTitle: {ticket['title']}"
      response += f"\nState: {ticket['state_id']}"
      response += f"\nPriority: {ticket['priority_id']}"
      response += f"\nCreated At: {ticket['created_at']}"
      response += f"\nUpdated At: {ticket['updated_at']}"

      response += "\n\nArticles:"
      for article in unique_articles:
        response += f"\nArticle ID: {article['id']}"
        response += f"\nFrom: {article['from']}"
        response += f"\nTo: {article['to']}"
        response += f"\nCC: {article['cc']}"
        response += f"\nSubject: {article['subject']}"
        response += f"\nCreated At: {article['created_at']}"
        response += f"\nUpdated At: {article['updated_at']}"
        response += f"\nBody:\n{article['body']}"
        response += "\n" + ("-" * 50)

    except Exception as e:
      response = f"Error getting ticket details: {str(e)}"

    return response

  def list_tags(self, ticket_id: int) -> list:
    """List all tags for a specific ticket."""
    try:
      response = self.get(f"tags?object=Ticket&o_id={ticket_id}")
      return response.get("tags", [])
    except Exception as e:
      print(f"Error listing tags for ticket {ticket_id}: {str(e)}")
      return []

  def remove_tag(self, ticket_id: int, tag: str) -> bool:
    """Remove a specific tag from a ticket."""
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      # The endpoint documentation shows DELETE, but since we're using _make_request,
      # we'll need to add DELETE support to it
      response = self._make_request('delete', "tags/remove", data)
      print(f"Successfully removed tag '{tag}' from ticket {ticket_id}")
      return True
    except Exception as e:
      print(f"Error removing tag '{tag}' from ticket {ticket_id}: {str(e)}")
      return False



##################################################
#                 COMMAND CLASS                  #
##################################################
class ModuleCommands(Command):
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
  def list_tickets(self, settings: Settings, query: str = "open-tickets") -> str:
    """
    List tickets from Zammad based on a query.

    Args:
      settings: Application settings
      query: Query name or custom query string

    Returns:
      str: List of tickets
    """
    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables."

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Get tickets
    tickets = zammad.list_tickets(query)

    # Format the response
    if not tickets:
      return "No tickets found."

    response = f"Found {len(tickets)} tickets:\n\n"
    for ticket_id in tickets:
      response += f"- Ticket ID: {ticket_id}\n"

    return response

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
  def get_ticket_details(self, settings: Settings, ticket_id: str) -> str:
    """
    Get details of a specific ticket from Zammad.

    Args:
      settings: Application settings
      ticket_id: The ID of the ticket to retrieve

    Returns:
      str: Ticket details
    """
    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables."

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Get ticket details
    return zammad.get_ticket_details(ticket_id)

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
  def add_tag(self, settings: Settings, ticket_id: str, tag: str) -> str:
    """
    Add a tag to a ticket in Zammad.

    Args:
      settings: Application settings
      ticket_id: The ID of the ticket to tag
      tag: The tag to add to the ticket

    Returns:
      str: Result message
    """
    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables."

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Add tag to ticket
    result = zammad.add_tag(ticket_id, tag)

    if result:
      return f"Successfully added tag '{tag}' to ticket {ticket_id}."
    else:
      return f"Failed to add tag '{tag}' to ticket {ticket_id}."

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
  def remove_tag(self, settings: Settings, ticket_id: str, tag: str) -> str:
    """
    Remove a tag from a ticket in Zammad.

    Args:
      settings: Application settings
      ticket_id: The ID of the ticket
      tag: The tag to remove from the ticket

    Returns:
      str: Result message
    """
    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables."

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Remove tag from ticket
    result = zammad.remove_tag(ticket_id, tag)

    if result:
      return f"Successfully removed tag '{tag}' from ticket {ticket_id}."
    else:
      return f"Failed to remove tag '{tag}' from ticket {ticket_id}."

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
  def process_tickets(self, settings: Settings) -> str:
    """
    Process untagged tickets and add AI tags.

    Args:
      settings: Application settings

    Returns:
      str: Processing result
    """
    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables."

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Process tickets
    result = zammad_run_process(settings, zammad)
    return "Ticket processing completed."

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
  def untag_tickets(self, settings: Settings) -> str:
    """
    Remove AI tags from all tagged tickets.

    Args:
      settings: Application settings

    Returns:
      str: Untagging result
    """
    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables."

    # Create Zammad API client
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Remove AI tags
    tickets = zammad.list_tickets("tagged-tickets")

    if not tickets:
      return "No tagged tickets found"

    removed_count = 0

    for ticket_id in tickets:
      tags = zammad.list_tags(ticket_id)
      ai_tags = [tag for tag in tags if tag.startswith("AI-")]

      if ai_tags:
        for tag in ai_tags:
          if zammad.remove_tag(ticket_id, tag):
            removed_count += 1

    return f"Completed! Removed {removed_count} AI tags from {len(tickets)} tickets"



##################################################
#                   FUNCTIONS                    #
##################################################
def zammad_run_process(settings: Settings, zammad: ZammadAPI) -> Result:
  # Import here to avoid circular imports
  from models import run as model_run

  result = Result()
  tickets = zammad.list_tickets("untagged-tickets")
  temp_tickets = tickets[11:]  # Select the first ticket for demonstration purposes

  for selected_ticket in temp_tickets:
    ticket_details = zammad.get_ticket_details(selected_ticket)
    tagging_messages = [
      {"role": "system", "content": zammad_tag_prompt},
      {"role": "user", "content": ticket_details}
    ]

    print("-" * 50)
    print("-" * 50)
    print(f"RAW TICKET DATA:\n{ticket_details}")

    tagging_result = model_run(settings.active_model, tagging_messages, settings=settings)
    if tagging_result.is_error():
      print(f"Error running tagging model: {tagging_result.get_message()}")
    else:
      print("-" * 50)
      print(f"Tagging Result:\n{tagging_result.data}")
      print("-" * 50)
      # Remove any escape characters and check for tags
      if tagging_result.data:
        cleaned_response = tagging_result.data.replace("\\", "")
        try:
          if cleaned_response and "[TAG]" in cleaned_response and "[/TAG]" in cleaned_response:
            start = cleaned_response.index("[TAG]") + len("[TAG]")
            end = cleaned_response.index("[/TAG]")
            tag = cleaned_response[start:end].strip()

            if tag in ["Phishing", "Spam", "Completed", "NetworkHardware", "Jenzabar", "LMS", "Report", "Printers", "Forms", "Adobe", "InfoMaker", "Salesforce", "Classroom", "Login", "Student", "Filter", "Video", "AccountManagement", "NoCategoryFound"]:
              zammad.add_tag(selected_ticket, f"AI-{tag}")
            else:
              zammad.add_tag(selected_ticket, "AI-Unknown")
          else:
            print("Missing tag markers in response, using AI-Blank")
            zammad.add_tag(selected_ticket, "AI-Blank")
        except Exception as e:
          print(f"Error extracting tag: {e}, using AI-Error")
          zammad.add_tag(selected_ticket, "AI-Error")

        zammad.add_tag(selected_ticket, "AI-Tagged")

  return result



##################################################
#                   PROMPTS                      #
##################################################
zammad_summarize_prompt = f"""
You are an expert IT professional. You offer all sorts of support ranging from simple device advice to complex education software systems. You are tasked with summarizing and describing all relevant information about a provided ticket. Don't make any note on whether or not this is submitted by a student, staff, or faculty.

Some of these tickets may be requests for support, reminders from IT personel for projects, email chains between multiple various people or departments, even just normal software or computer problems. Some requests may even be unrelated or phishing/marketing emails. These tickets may also contain repeating information just like you would find in an email reply chain.

You should analyze the ticket. If there is not enough context then suggest a response that will gather more info.

Your response should follow this layout:
- First, describe all of your thoughts or observations about the ticket.
- Next, summarize the ticket, whether or not it has been completed, whether or not there are multiple facets to this tickets, wheter or not it's relevant.
- Finally suggest a potential response, even if the best response is to ignore or close the ticket. Be explicit and show your reasoning.
"""

zammad_tag_prompt = f"""
You are a helpful and harmless assistant. You are Qwen developed by Alibaba. You should think step-by-step.

You are organizing tickets into categories and assigning relevant tags. Consider which category fits the ticket best. But when in doubt, use the "NoCategoryFound" tag. You never want to have inaccurate tags.

Here are the available tags. Your response MUST contain an entry from this list:
- Phishing (any emails or links that have been sent in for review, or any otherwise suspicious 3rd party emails or links)
- Spam (any marketing emails or quarantine emails)
- Completed (*this tag takes precedence for anything that fits, anything that looks completed, such as a ticket with a thank you at the end, or something that seems trivial to resolve but is very old)
- NetworkHardware (any network hardware related issues such as switches, routers, firewalls, access points, or anything that might require physical hardware installation or maintenance)
- Jenzabar (anything about the Jenzabar software)
- LMS (anything about course setup, assignment creation or grading, etc)
- Report (anything about informative reporting or reporting services)
- Printers (anything related to printers or printing, including drivers or driver installs, toners need changing, etc)
- Forms (a webform needs updating, the emails are going to the wrong recipient, new form needed, etc)
- Adobe (anything requested about the Adobe software or licenses)
- InfoMaker (anything requested about the InfoMake software or related processes)
- Salesforce (anything requested about the Salesforce platform or related issues)
- Classroom (anything related to classroom troubles, teacher's computer not turning on, smartboard not working, projector is dim, etc)
- Login (locked out of account, needs password reset, can't find username or password, MFA trouble, etc)
- Student (any student submitted request that doesn't fit the other categories, these would likely be simple issues, this could be trouble with an office license, library access issues, laptop is having trouble, etc)
- Filter (the website filter, wifi is blocking a device's access)
- Video (any video uploads or class videos if requested by a faculty or staff member. This includes Zoom, YouTube, Teams Meetings, and misc recordings)
- AccountManagement (misc account management issues, such as disabling or adding permissions, updating account names, etc)
- NoCategoryFound (use this if no other category seems related or is just not a good fit)

Assign a tag using the following format:
[TAG]tag_name[/TAG]

Example 1:
[TAG]Phishing[/TAG]

Example 2:
[TAG]NoCategoryFound[/TAG]

Notes:
- You MUST use the above tags.
- You MUST use the tag name exactly as it is listed above.
- You MUST use the [TAG] and [/TAG] format.
- The tag MUST start with [TAG] and end with [/TAG].

Respond to the user's request by assigning the appropriate tag. The answer MUST be one of the above tags.
"""