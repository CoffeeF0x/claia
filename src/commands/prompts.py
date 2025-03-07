from commands.base import Command, command
from errors import Result
from settings import Settings
from typing import Dict



##################################################
#                 COMMAND CLASS                  #
##################################################
class PromptCommand(Command):

  @command(
    path=["list"],
    description="List all available prompts or details about a specific prompt",
    help_text="List all available prompts or details about a specific prompt",
    parameters={
      "type": "object",
      "properties": {
        "prompt_name": {
          "type": "string",
          "description": "Optional name of a specific prompt to show details for"
        }
      }
    }
  )
  def list_prompts(self, settings: Settings, prompt_name: str = "") -> str:
    """List all available prompts or details about a specific prompt"""
    if prompt_name:
      prompt = next((p for p in settings.prompt_store if p.name == prompt_name), None)
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
        message = f"Prompt '{prompt_name}' not found"
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
    description="Remove the current prompt selection",
    help_text="Remove the current prompt selection",
    aliases=["unset"]
  )
  def remove_prompt(self, settings: Settings) -> str:
    """Remove the current prompt selection"""
    settings.active_prompt = None
    message = "Active prompt removed"
    print(message)
    return message

  @command(
    path=["set"],
    description="Select a prompt to use in the conversation",
    help_text="Select a prompt to use in the conversation",
    aliases=["select"],
    parameters={
      "type": "object",
      "properties": {
        "prompt_name": {
          "type": "string",
          "description": "Name of the prompt to select"
        }
      },
      "required": ["prompt_name"]
    }
  )
  def set_prompt(self, settings: Settings, prompt_name: str) -> str:
    """Select a prompt to use in the conversation"""
    prompt = settings.get_prompt(prompt_name)
    if prompt:
      settings.active_prompt = prompt
      message = f"Selected prompt: {settings.active_prompt.title}"
      print(message)
      return message
    else:
      message = f"Prompt '{prompt_name}' not found"
      print(message)
      return message

  @command(
    path=["print"],
    description="Display the current prompt selection",
    help_text="Display the current prompt selection",
    aliases=["current"]
  )
  def current_prompt(self, settings: Settings) -> str:
    """Display the current prompt selection"""
    if settings.active_prompt:
      message = f"Current prompt: {settings.active_prompt.title}"
      print(message)
      return message
    else:
      message = "No prompt selected"
      print(message)
      return message