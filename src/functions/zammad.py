# External dependencies
import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
from typing import List

from aia import AIASession
from tempfile import NamedTemporaryFile

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
      else:
          raise ValueError(f"Unsupported HTTP method: {method}")

    response.raise_for_status()
    return response.json()

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
      response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}")
      tickets = response["tickets"]
      ticket_count = response["tickets_count"]
      print(f"tickets: {ticket_count}")

      while full_response and response["tickets_count"] > 0:
        print(f"total tickets: {ticket_count}")
        page += 1
        response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}")
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