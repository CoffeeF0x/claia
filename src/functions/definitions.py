import json

functions = [
  {
    "name": "get_current_time",
    "description": "Returns the current time",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The current time in HH:MM:SS format"
    }
  },
  {
    "name": "get_current_date",
    "description": "Returns the current date",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The current date in YYYY-MM-DD format"
    }
  },
  {
    "name": "get_user_name",
    "description": "Returns a hardcoded user name",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The hardcoded user name"
    }
  },
  {
    "name": "greet_user",
    "description": "Greets a user by name",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "The name of the user to greet"
          }
        },
      "required": ["name"]
    },
    "returns": {
      "type": "string",
      "description": "A greeting message"
    }
  },
  {
    "name": "list_tickets",
    "description": "Get a list of tickets IDs from Zammad",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "A list of ticket IDs"
    }
  },
  {
    "name": "get_ticket_details",
    "description": "Get details for a Zammad ticket using its ID",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "the ticket id"
          }
        },
      "required": ["id"]
    },
    "returns": {
      "type": "string",
      "description": "the ticket details and articles in a human readable format"
    }
  }
]

function_format = f"""
[FUNCTION_CALL]{{
"name": "function_name",
"parameters": {{
  "param1": "value1",
  "param2": "value2"
}}
}}[/FUNCTION_CALL]
"""

prompt = f"""
You are an AI assistant capable of calling functions. Here are the available functions:

{json.dumps(functions, indent=2)}

When you need to call a function, use the following format:
{function_format}

Respond to the user's request by calling the appropriate function when necessary.
"""

zammad_summarize_prompt = f"""
You are an expert IT professional. You offer all sorts of support ranging from simple device advice to complex education software systems. You are tasked with summarizing and describing all relevant information about a provided ticket.

Some of these tickets may be requests for support, reminders from IT personel for projects, email chains between multiple various people or departments, even just normal software or computer problems. Some requests may even be unrelated or phishing/marketing emails. These tickets may also contain repeating information just like you would find in an email reply chain.

You should analyze the ticket. If there is not enough context then suggest a response that will gather more info.

Your response should follow this layout:
- First, describe all of your thoughts or observations about the ticket.
- Next, summarize the ticket, whether or not it has been completed, whether or not there are multiple facets to this tickets, wheter or not it's relevant.
- Finally suggest a category and a potential response, even if the best response is to ignore or close the ticket. Be explicit and show your reasoning.
"""

zammad_tag_prompt = f"""
You are an IT professional and an expert in customer support. You are tasked with reviewing a user's request and based on the information provided, assign the best related tag to the ticket.

Here are the available tags. You MUST choose an entry from this list:
- Phishing (any emails or links that have been sent in for review, or any otherwise suspicious 3rd party emails or links)
- Spam (any marketing emails or quarantine emails)
- Completed (anything that looks completed, but is still in this list, such as a ticket with a thank you at the end, or something that seems trivial but is very old)
- NetworkHardware (any network hardware related issues such as switches, routers, firewalls, access points, or anything that might require physical hardware installation or maintenance)
- Jenzabar (anything about this software)
- LMS (anything about course setup, assignment creation or grading, etc)
- Report (anything about informative reporting or reporting services)
- Printers (anything related to printers or printing, including drivers or driver installs, toners need changing, etc)
- Forms (a webform needs updating, the emails are going to the wrong recipient, new form needed, etc)
- Adobe (anything requested about this software)
- InfoMaker (anything requested about this software)
- Salesforce (anything requested about this software)
- Classroom (anything related to classroom troubles, teacher's computer not turning on, smartboard not working, projector is dim, etc)
- Login (locked out of account, needs password reset, can't find username or password, MFA trouble, etc)
- Student (an other student request, this could be trouble with office, library access issues, laptop is having trouble, etc)
- Filter (the website filter, wifi is blocking a device's access)
- NoCategoryFound (use this if no other category seems related or is just not a good fit)

Assign a tag using the following format:
[TAG]tag_name[/TAG]
"""