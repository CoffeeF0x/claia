# External dependencies
import json

# Internal dependencies
from commands.base import Command
from errors import Result
from settings import Settings

# Module dependencies
from modules.zammad.api import ZammadAPI
from modules.zammad.settings import get_settings, ENV_ZAMMAD_API_TOKEN, ENV_ZAMMAD_BASE_URL



##################################################
#                 COMMAND CLASS                  #
##################################################
class ZammadCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return result.fail(f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables.")

    # Create Zammad API client
    zammad: ZammadAPI = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    if len(commands) > 1:
      if commands[1] == "list" or commands[1] == "query":
        if len(commands) > 2:
          print(zammad.list_tickets(commands[2]))
        else:
          print(zammad.list_tickets())
      elif commands[1] == "details" and len(commands) > 2:
        print(zammad.get_ticket_details(commands[2]))
      elif commands[1] == "test" and len(commands) > 2:
        print(zammad.get(commands[2]))
      elif commands[1] == "process":
        zammad_run_process(settings, zammad)
      elif commands[1] == "untag":
        zammad_remove_ai_tags(settings, zammad)
      else:
        print("Unrecognized zammad command")
        print_help()
    else:
      print_help()

    return result



##################################################
#                   FUNCTIONS                    #
##################################################
def zammad_run_process(settings: Settings, zammad: ZammadAPI) -> Result:
  # Import here to avoid circular imports
  from models import run as model_run

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

def zammad_remove_ai_tags(settings: Settings, zammad: ZammadAPI) -> Result:
  result: Result = Result()
  tickets = zammad.list_tickets("tagged-tickets")

  if not tickets:
    print("No tagged tickets found")
    return result

  print(f"Found {len(tickets)} tagged tickets. Processing...")
  removed_count = 0

  for ticket_id in tickets:
    tags = zammad.list_tags(ticket_id)
    ai_tags = [tag for tag in tags if tag.startswith("AI-")]

    if ai_tags:
      print(f"\nRemoving {len(ai_tags)} AI tags from ticket {ticket_id}:")
      for tag in ai_tags:
        if zammad.remove_tag(ticket_id, tag):
          removed_count += 1

  print(f"\nCompleted! Removed {removed_count} AI tags from {len(tickets)} tickets")
  return result

def print_help():
  """Print help information for zammad commands."""
  print("Zammad Commands:")
  print("  zammad list [query]      - List tickets (optional query)")
  print("  zammad details <id>      - Show ticket details")
  print("  zammad test <endpoint>   - Test API endpoint")
  print("  zammad process           - Process untagged tickets")
  print("  zammad untag             - Remove AI tags from tickets")

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