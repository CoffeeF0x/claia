from commands.base import Command, command
from errors import Result
from settings import Settings
from typing import Dict



##################################################
#                 COMMAND CLASS                  #
##################################################
class CharacterCommand(Command):

  @command(
    path=["list"],
    description="List all available characters or details about a specific character",
    help_text="List all available characters or details about a specific character",
    parameters={
      "type": "object",
      "properties": {
        "character_name": {
          "type": "string",
          "description": "Optional name of a specific character to show details for"
        }
      }
    }
  )
  def list_characters(self, settings: Settings, character_name: str = "") -> str:
    """List all available characters or details about a specific character"""
    if character_name:
      prompt = next((p for p in settings.prompt_store if p.name == character_name), None)
      if prompt:
        output = [
          f"Name: {prompt.name}",
          f"Title: {prompt.title}",
          f"Prompt: {prompt.prompt}"
        ]
        if prompt.description:
          output.append(f"Description: {prompt.description}")
        print("\n".join(output))
        return "\n".join(output)
      else:
        message = f"Character '{character_name}' not found"
        print(message)
        return message
    else:
      output = []
      for prompt in settings.prompt_store:
        output.append(f"{prompt.name}: {prompt.title}")
      print("\n".join(output))
      return "\n".join(output)

  @command(
    path=["remove"],
    description="Remove the current character selection",
    help_text="Remove the current character selection",
    aliases=["unset"]
  )
  def remove_character(self, settings: Settings) -> str:
    """Remove the current character selection"""
    settings.active_prompt = None
    message = "Active character removed"
    print(message)
    return message

  @command(
    path=["set"],
    description="Select a character to use in the conversation",
    help_text="Select a character to use in the conversation",
    aliases=["select"],
    parameters={
      "type": "object",
      "properties": {
        "character_name": {
          "type": "string",
          "description": "Name of the character to select"
        }
      },
      "required": ["character_name"]
    }
  )
  def set_character(self, settings: Settings, character_name: str) -> str:
    """Select a character to use in the conversation"""
    prompt = settings.get_prompt(character_name)
    if prompt:
      settings.active_prompt = prompt
      message = f"Selected character: {settings.active_prompt.title}"
      print(message)
      return message
    else:
      message = f"Character '{character_name}' not found"
      print(message)
      return message

  @command(
    path=["print"],
    description="Display the current character selection",
    help_text="Display the current character selection",
    aliases=["current"]
  )
  def current_character(self, settings: Settings) -> str:
    """Display the current character selection"""
    if settings.active_prompt:
      message = f"Current character: {settings.active_prompt.title}"
      print(message)
      return message
    else:
      message = "No character selected"
      print(message)
      return message