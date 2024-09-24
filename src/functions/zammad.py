# External dependencies
import requests
import urllib.parse

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

  def get(self, endpoint: str):
    response = None
    url = f"{self.base_url}{endpoint}"
    cadata = self.session.cadata_from_url(url)

    with NamedTemporaryFile("w") as pem_file:
      pem_file.write(cadata)
      pem_file.flush()
      response = requests.get(url, headers=self.headers, verify=pem_file.name)

    response.raise_for_status()
    return response.json()

  def list_tickets(self, query_name: str = "open-tickets", limit: int = 100, full_response: bool = True):
    queries = {
      "new-tickets": "state_id:1",
      "open-tickets": "state_id:1 OR state_id:2 OR state_id:3",
      "reminder-tickets": "state_id:3",
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

  def get_ticket_details(self, ticket_id: str) -> None:
    response = ""

    try:
      ticket = self.get(f"tickets/{ticket_id}")
      articles = self.get(f"ticket_articles/by_ticket/{ticket_id}")

      response +=  "Ticket Details:"
      response +=  f"\nTicket ID: {ticket['id']}"
      response +=  f"\nNumber: {ticket['number']}"
      response +=  f"\nTitle: {ticket['title']}"
      response +=  f"\nState: {ticket['state_id']}"
      response +=  f"\nPriority: {ticket['priority_id']}"
      response +=  f"\nCreated At: {ticket['created_at']}"
      response +=  f"\nUpdated At: {ticket['updated_at']}"

      response +=  "\n\nArticles:"
      for article in articles:
        response +=  f"\nArticle ID: {article['id']}"
        response +=  f"\nFrom: {article['from']}"
        response +=  f"\nTo: {article['to']}"
        response +=  f"\nCC: {article['cc']}"
        response +=  f"\nSubject: {article['subject']}"
        response +=  f"\nCreated At: {article['created_at']}"
        response +=  f"\nUpdated At: {article['updated_at']}"
        response +=  f"\nBody:\n{article['body']}"
        response +=  "\n" + ("-" * 50)

    except Exception as e:
      response =  f"Error getting ticket details: {str(e)}"

    return response