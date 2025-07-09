"""
Zammad API client for Claia.

This module provides the API client for interacting with the Zammad ticketing system.
"""

# External dependencies
import logging
import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
from typing import List
from tempfile import NamedTemporaryFile

# Try to import AIA, but make it optional
try:
  from aia import AIASession
except ImportError:
  # Create a fallback class if AIA is not available
  class AIASession:
    def cadata_from_url(self, url):
      return ""

# Internal dependencies
from .constants import TICKET_QUERIES, SAFETY_LIMIT



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              API CLASS                               #
########################################################################
class ZammadAPI:
  """Class for interacting with the Zammad API."""

  def __init__(self, base_url: str, api_token: str) -> None:
    logger.debug(f"Initializing ZammadAPI with base_url: {base_url}")
    self.base_url = base_url
    self.api_token = api_token
    self.headers = {
      "Authorization": f"Token token={self.api_token}",
      "Content-Type": "application/json"
    }
    self.session = AIASession()
    logger.debug("ZammadAPI initialization complete")


  ######################################################################
  #                          PRIVATE METHODS                           #
  ######################################################################
  def _make_request(self, method: str, endpoint: str, data=None):
    """Make a request to the Zammad API with proper certificate handling."""

    url = f"{self.base_url}{endpoint}"
    logger.debug(f"Making {method} request to endpoint: {endpoint}")
    cadata = self.session.cadata_from_url(url)

    with NamedTemporaryFile("w") as pem_file:
      pem_file.write(cadata)
      pem_file.flush()
      logger.debug("Created temporary PEM file for certificate")

      try:
        if method.lower() == 'get':
          logger.debug("Sending GET request")
          response = requests.get(url, headers=self.headers, verify=pem_file.name)
        elif method.lower() == 'post':
          logger.debug(f"Sending POST request with data: {data}")
          response = requests.post(url, headers=self.headers, json=data, verify=pem_file.name)
        elif method.lower() == 'delete':
          logger.debug(f"Sending DELETE request with data: {data}")
          response = requests.delete(url, headers=self.headers, json=data, verify=pem_file.name)
        else:
          logger.error(f"Unsupported HTTP method: {method}")
          raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        logger.debug(f"Request successful with status code: {response.status_code}")
        return response.json() if response.content else None
      except Exception as e:
        logger.error(f"API request error ({method} {endpoint}): {str(e)}")
        raise


  def _clean_html_content(self, text: str) -> str:
    """Clean HTML content from ticket articles."""

    logger.debug(f"Cleaning HTML content of length: {len(text) if text else 0}")
    if not text:
      return ""

    # First use BeautifulSoup to handle HTML properly
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text(separator='\n')

    # Remove extra whitespace and normalize newlines
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text.strip())
    logger.debug(f"Cleaned text length: {len(clean_text)}")

    return clean_text


  def _extract_unique_content(self, articles: List[dict]) -> List[dict]:
    """Extract unique content from ticket articles to avoid duplication."""

    logger.debug(f"Extracting unique content from {len(articles)} articles")
    seen_content = set()
    unique_articles = []

    for article in articles:
      # Clean the body content
      clean_body = self._clean_html_content(article['body'])

      # Split into paragraphs and process each
      paragraphs = clean_body.split('\n\n')
      unique_paragraphs = []
      logger.debug(f"Processing {len(paragraphs)} paragraphs from article {article.get('id', 'unknown')}")

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

    logger.debug(f"Extracted {len(unique_articles)} unique articles from {len(articles)} original articles")
    return unique_articles


  ######################################################################
  #                         CORE REQUEST TYPES                         #
  ######################################################################
  def get(self, endpoint: str):
    """Make a GET request to the Zammad API."""

    logger.debug(f"Making GET request to endpoint: {endpoint}")
    return self._make_request('get', endpoint)


  def post(self, endpoint: str, data: dict):
    """Make a POST request to the Zammad API."""

    logger.debug(f"Making POST request to endpoint: {endpoint} with data: {data}")
    return self._make_request('post', endpoint, data)


  def delete(self, endpoint: str, data: dict):
    """Make a DELETE request to the Zammad API."""

    logger.debug(f"Making DELETE request to endpoint: {endpoint} with data: {data}")
    return self._make_request('delete', endpoint, data)


  ######################################################################
  #                           PUBLIC METHODS                           #
  ######################################################################
  def add_tag(self, ticket_id: int, tag: str) -> bool:

    """
    Add a tag to a ticket.

    Args:
      ticket_id: The ID of the ticket
      tag: The tag to add

    Returns:
      bool: True if successful, False otherwise
    """

    logger.debug(f"Adding tag '{tag}' to ticket {ticket_id}")
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      self.post("tags/add", data)
      logger.info(f"Successfully added tag '{tag}' to ticket {ticket_id}")
      return True
    except Exception as e:
      logger.error(f"Error adding tag '{tag}' to ticket {ticket_id}: {str(e)}")
      return False


  def list_tickets(
    self,
    query_name: str = "open-tickets",
    limit: int = 100,
    full_response: bool = False):

    """
    List tickets based on a predefined query or custom query string.

    Args:
      query_name: Name of predefined query or custom query string
      limit: Maximum number of tickets per page

    Returns:
      List of ticket objects or None if an error occurred
    """

    logger.debug(f"Listing tickets with query: {query_name}, limit: {limit}, full_response: {full_response}")
    query = TICKET_QUERIES.get(query_name, query_name)
    encoded_query = urllib.parse.quote(query)
    logger.debug(f"Using encoded query: {encoded_query}")

    try:
      # Get the first page of results
      page = 1
      response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
      ticket_ids = response["tickets"]
      assets = response["assets"]
      ticket_count = response["tickets_count"]
      tickets = []
      logger.debug(f"Initial page retrieved with {ticket_count} tickets")

      # If full_response is True, fetch all pages
      while full_response and response["tickets_count"] > 0 and page * limit < SAFETY_LIMIT:
        logger.debug(f"Fetching page {page + 1}, total tickets so far: {ticket_count}")
        page += 1
        response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
        ticket_ids.extend(response["tickets"])
        assets.extend(response["assets"])
        ticket_count += response["tickets_count"]

      # Extract various assets
      asset_tickets = assets["Ticket"]
      asset_users   = assets["User"]
      asset_groups  = assets["Group"]
      asset_roles   = assets["Role"]

      # Append ticket information for each ticket id
      for ticket in asset_tickets.values():
        tickets.append(ticket)

      logger.info(f"Created {len(tickets)} ticket objects")
      return tickets
    except Exception as e:
      logger.error(f"Error listing tickets: {str(e)}")
      return None


  def get_ticket_details(self, ticket_id: str, compact: bool = False) -> str:

    """
    Get detailed information about a ticket.

    Args:
      ticket_id: The ID of the ticket
      compact: Show compact view without full message bodies

    Returns:
      str: Formatted ticket details
    """

    logger.debug(f"Getting details for ticket ID: {ticket_id}")
    try:
      # Get ticket and article data
      ticket = self.get(f"tickets/{ticket_id}")
      articles = self.get(f"ticket_articles/by_ticket/{ticket_id}")
      logger.debug(f"Retrieved ticket data and {len(articles)} articles")

      # Process articles to remove duplicates
      unique_articles = self._extract_unique_content(articles)
      logger.debug(f"Processed {len(unique_articles)} unique articles")

      # Format the response
      width = 78  # Total width of the box
      response = [f"┌{'─' * width}┐"]
      response.append(f"│ {'TICKET DETAILS':^{width-2}} │")
      response.append(f"├{'─' * width}┤")

      # Ticket information section
      response.append(f"│ {'Ticket ID:':<15} {ticket['id']:<{width-18}} │")
      response.append(f"│ {'Number:':<15} {ticket['number']:<{width-18}} │")
      response.append(f"│ {'Title:':<15} {ticket['title']:<{width-18}} │")
      response.append(f"│ {'State:':<15} {ticket.get('state', str(ticket['state_id'])):<{width-18}} │")
      response.append(f"│ {'Priority:':<15} {ticket.get('priority', str(ticket['priority_id'])):<{width-18}} │")

      # Format dates nicely
      created_at = ticket['created_at']
      updated_at = ticket['updated_at']
      try:
        import datetime
        created_dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        updated_dt = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        created_at = created_dt.strftime('%Y-%m-%d %H:%M:%S')
        updated_at = updated_dt.strftime('%Y-%m-%d %H:%M:%S')
      except Exception:
        pass

      response.append(f"│ {'Created At:':<15} {created_at:<{width-18}} │")
      response.append(f"│ {'Updated At:':<15} {updated_at:<{width-18}} │")

      # Show tags if present
      tags = ticket.get('tags', [])
      if tags:
        tags_str = ', '.join(tags)
        response.append(f"│ {'Tags:':<15} {tags_str:<{width-18}} │")

      # Add a separator before articles
      response.append(f"├{'─' * width}┤")
      response.append(f"│ {'CONVERSATION HISTORY':^{width-2}} │")
      response.append(f"├{'─' * width}┤")

      # Handle no articles case
      if not unique_articles:
        response.append(f"│ {'No conversation history found':^{width-2}} │")
        response.append(f"└{'─' * width}┘")
        return "\n".join(response)

      # Process and display each article
      for i, article in enumerate(unique_articles):
        # Article header
        response.append(f"│ {'Message #' + str(i+1):^{width-2}} │")
        response.append(f"├{'─' * width}┤")
        response.append(f"│ {'From:':<10} {article.get('from', 'Unknown'):<{width-13}} │")

        # Only show To/CC fields if they have content
        if article.get('to'):
          response.append(f"│ {'To:':<10} {article.get('to', ''):<{width-13}} │")
        if article.get('cc'):
          response.append(f"│ {'CC:':<10} {article.get('cc', ''):<{width-13}} │")

        response.append(f"│ {'Subject:':<10} {article.get('subject', ''):<{width-13}} │")

        # Format date
        art_created = article.get('created_at', '')
        try:
          import datetime
          art_dt = datetime.datetime.fromisoformat(art_created.replace('Z', '+00:00'))
          art_created = art_dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
          pass
        response.append(f"│ {'Date:':<10} {art_created:<{width-13}} │")

        # Display body content with proper formatting
        response.append(f"├{'─' * width}┤")

        # If compact mode, show truncated body or skip body
        body = article.get('body', '')
        if compact:
          if body:
            # Show a preview (first 100 chars)
            preview = body.replace('\n', ' ').strip()[:100]
            if len(body) > 100:
              preview += '...'
            response.append(f"│ {preview:<{width-2}} │")
        else:
          # Full message display with word wrapping for better formatting
          if body:
            # Split body into lines, respecting both explicit newlines and word wrapping
            lines = []
            for line in body.split('\n'):
              # Handle long lines by breaking them at width-4 chars (leaving space for border and padding)
              while line and len(line) > width-4:
                # Try to break at a space if possible
                break_point = line[:width-4].rfind(' ')
                if break_point == -1 or break_point < 30:  # If no good break point, just cut it
                  break_point = width-4
                lines.append(line[:break_point])
                line = line[break_point:].lstrip()
              if line:
                lines.append(line)

            # Display each line with proper borders
            for line in lines:
              response.append(f"│ {line:<{width-2}} │")
          else:
            response.append(f"│ {'(No content)':<{width-2}} │")

        # Add a separator between articles
        if i < len(unique_articles) - 1:
          response.append(f"├{'─' * width}┤")
        else:
          response.append(f"└{'─' * width}┘")

      # Add command hint for compact mode toggle
      if compact:
        response.append("\nTo view full message bodies:")
        response.append(f"claia zammad details {ticket_id}")
      else:
        response.append("\nFor a more compact view:")
        response.append(f"claia zammad details {ticket_id} --compact")

      logger.debug("Successfully formatted ticket details")
      return "\n".join(response)
    except Exception as e:
      logger.error(f"Error getting ticket details: {str(e)}")
      return f"Error getting ticket details: {str(e)}"


  def list_tags(self, ticket_id: int) -> list:

    """
    List all tags for a specific ticket.

    Args:
      ticket_id: The ID of the ticket

    Returns:
      list: List of tags
    """

    logger.debug(f"Listing tags for ticket ID: {ticket_id}")
    try:
      response = self.get(f"tags?object=Ticket&o_id={ticket_id}")
      tags = response.get("tags", [])
      logger.debug(f"Retrieved {len(tags)} tags for ticket {ticket_id}")
      return tags
    except Exception as e:
      logger.error(f"Error listing tags for ticket {ticket_id}: {str(e)}")
      return []


  def remove_tag(self, ticket_id: int, tag: str) -> bool:

    """
    Remove a specific tag from a ticket.

    Args:
      ticket_id: The ID of the ticket
      tag: The tag to remove

    Returns:
      bool: True if successful, False otherwise
    """

    logger.debug(f"Removing tag '{tag}' from ticket {ticket_id}")
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      self.delete("tags/remove", data)
      logger.info(f"Successfully removed tag '{tag}' from ticket {ticket_id}")
      return True
    except Exception as e:
      logger.error(f"Error removing tag '{tag}' from ticket {ticket_id}: {str(e)}")
      return False


  def delete_ticket(self, ticket_id: int) -> bool:

    """
    Delete a specific ticket from Zammad.

    Args:
      ticket_id: The ID of the ticket to delete

    Returns:
      bool: True if successful, False otherwise
    """

    logger.debug(f"Deleting ticket with ID: {ticket_id}")
    try:
      self.delete(f"tickets/{ticket_id}", {})
      logger.info(f"Successfully deleted ticket with ID: {ticket_id}")
      return True
    except Exception as e:
      logger.error(f"Error deleting ticket with ID {ticket_id}: {str(e)}")
      return False