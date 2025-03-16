import logging
from typing import Dict, List
import json
import os

# Internal Dependencies
from commands.base import Command, command
from errors import Result
from settings import Settings
from conversations.prompts import Prompt



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
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
      # Get specific prompt details
      prompt = settings.get_prompt(prompt_name)
      if prompt:
        output = [
          f"Name: {prompt.name}",
          f"Title: {prompt.title}",
          f"Description: {prompt.description}",
          f"Prompt: {prompt.get_formatted_prompt()}"
        ]
        return "\n".join(output)
      else:
        return f"Prompt '{prompt_name}' not found"
    else:
      # List all prompts
      output = []
      for prompt in settings.prompt_store:
        output.append(f"{prompt.name}: {prompt.title}")
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
    return "Active prompt removed"

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
      return f"Selected prompt: {settings.active_prompt.title}"
    else:
      return f"Prompt '{prompt_name}' not found"

  @command(
    path=["print"],
    description="Display the current prompt selection",
    help_text="Display the current prompt selection",
    aliases=["current"]
  )
  def current_prompt(self, settings: Settings) -> str:
    """Display the current prompt selection"""
    if settings.active_prompt:
      return f"Current prompt: {settings.active_prompt.title}"
    else:
      return "No prompt selected"

  @command(
    path=["create"],
    description="Create a new prompt or update an existing one",
    help_text="Create a new prompt or update an existing one",
    aliases=["update"],
    parameters={
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the prompt (used as identifier)"
        },
        "title": {
          "type": "string",
          "description": "Display title for the prompt"
        },
        "prompt": {
          "type": "string",
          "description": "The prompt template text"
        },
        "description": {
          "type": "string",
          "description": "Optional description of the prompt"
        }
      },
      "required": ["name", "title", "prompt"]
    }
  )
  def create_prompt(self, settings: Settings, name: str, title: str, prompt: str, description: str = "") -> str:
    """Create a new prompt or update an existing one"""
    # Check if prompt already exists
    existing_prompt = settings.get_prompt(name)

    # Create or update the prompt
    new_prompt = Prompt(
      base_directory=settings.prompt_directory,
      name=name,
      title=title,
      prompt=prompt,
      description=description
    )

    # Save the prompt
    saved_path = new_prompt.save()

    if saved_path:
      # Reload all prompts to update the prompt_store
      settings.load_all_prompts()

      if existing_prompt:
        return f"Updated prompt: {name}"
      else:
        return f"Created new prompt: {name}"
    else:
      return f"Failed to save prompt: {name}"

  @command(
    path=["delete"],
    description="Delete a prompt",
    help_text="Delete a prompt",
    aliases=["remove-prompt"],
    parameters={
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the prompt to delete"
        },
        "confirm": {
          "type": "boolean",
          "description": "Confirm deletion (required for safety)"
        }
      },
      "required": ["name", "confirm"]
    }
  )
  def delete_prompt(self, settings: Settings, name: str, confirm: bool) -> str:
    """Delete a prompt"""
    if not confirm:
      return "Deletion not confirmed. Use confirm=true to delete the prompt."

    # Check if prompt exists
    existing_prompt = settings.get_prompt(name)
    if not existing_prompt:
      return f"Prompt '{name}' not found"

    # Check if it's the active prompt
    if settings.active_prompt and settings.active_prompt.name == existing_prompt.name:
      return f"Cannot delete the active prompt. Use 'prompt remove' to unset it first."

    # Delete the prompt
    formatted_name = Prompt.validate_and_format_name(name)
    deleted = Prompt.delete(formatted_name, settings.prompt_directory)

    if deleted:
      # Reload all prompts to update the prompt_store
      settings.load_all_prompts()
      return f"Deleted prompt: {name}"
    else:
      return f"Failed to delete prompt: {name}"