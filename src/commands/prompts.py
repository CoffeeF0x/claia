import logging
from typing import Dict, List

# Internal Dependencies
from .base import Command, command
from results import Result
from settings import Settings
from files import Prompt



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
  def list_prompts(self, settings: Settings, prompt_name: str = "") -> Result:
    """List all available prompts or details about a specific prompt"""
    result = Result()

    if prompt_name:
      # Get specific prompt details
      prompt = Prompt.load_prompt(prompt_name, settings.files_directory)
      if prompt:
        output = [
          f"Name: {prompt.prompt_name}",
          f"Prompt: {prompt.prompt_text}"
        ]
        result.data = "\n".join(output)
        result.message = "\n".join(output)
      else:
        result = Result.fail(f"Prompt '{prompt_name}' not found")
    else:
      # List all prompts
      prompts = Prompt.find_files_by_criteria(
        base_directory=settings.files_directory,
        subdirectory="prompts"
      )

      if not prompts:
        result.data = "No prompts found"
        result.message = "No prompts found"
      else:
        output = []
        for _, prompt_meta in prompts.items():
          prompt_name = prompt_meta.get("metadata", {}).get("prompt_name", "Unknown")
          output.append(f"{prompt_name}")

        result.data = "\n".join(output)
        result.message = "\n".join(output)

    return result

  @command(
    path=["remove"],
    description="Remove the current prompt selection",
    help_text="Remove the current prompt selection",
    aliases=["unset"]
  )
  def remove_prompt(self, settings: Settings) -> Result:
    """Remove the current prompt selection"""
    result = Result()
    settings.active_prompt = None
    result.message = "Active prompt removed"
    return result

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
  def set_prompt(self, settings: Settings, prompt_name: str) -> Result:
    """Select a prompt to use in the conversation"""
    result = Result()

    prompt = Prompt.load_prompt(prompt_name, settings.files_directory)
    if prompt:
      settings.active_prompt = prompt
      result.message = f"Selected prompt: {prompt.prompt_name}"
    else:
      result = Result.fail(f"Prompt '{prompt_name}' not found")

    return result

  @command(
    path=["print"],
    description="Display the current prompt selection",
    help_text="Display the current prompt selection",
    aliases=["current"]
  )
  def current_prompt(self, settings: Settings) -> Result:
    """Display the current prompt selection"""
    result = Result()

    if settings.active_prompt:
      result.message = f"Current prompt: {settings.active_prompt.prompt_name}"
    else:
      result.message = "No prompt selected"

    return result

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
        "prompt_text": {
          "type": "string",
          "description": "The prompt template text"
        }
      },
      "required": ["name", "prompt_text"]
    }
  )
  def create_prompt(self, settings: Settings, name: str, prompt_text: str) -> Result:
    """Create a new prompt or update an existing one"""
    result = Result()

    # Check if prompt already exists
    existing_prompt = Prompt.load_prompt(name, settings.files_directory)

    # Create or update the prompt
    prompt = Prompt.create_prompt(
      base_directory=settings.files_directory,
      prompt_name=name,
      prompt_text=prompt_text
    )

    if prompt:
      if existing_prompt:
        result.message = f"Updated prompt: {name}"
      else:
        result.message = f"Created new prompt: {name}"
    else:
      result = Result.fail(f"Failed to save prompt: {name}")

    return result

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
  def delete_prompt(self, settings: Settings, name: str, confirm: bool) -> Result:
    """Delete a prompt"""
    result = Result()

    if not confirm:
      return Result.fail("Deletion not confirmed. Use confirm=true to delete the prompt.")

    # Check if prompt exists
    existing_prompt = Prompt.load_prompt(name, settings.files_directory)
    if not existing_prompt:
      return Result.fail(f"Prompt '{name}' not found")

    # Check if it's the active prompt
    if settings.active_prompt and settings.active_prompt.prompt_name == existing_prompt.prompt_name:
      return Result.fail(f"Cannot delete the active prompt. Use 'prompt remove' to unset it first.")

    # Delete the prompt
    if existing_prompt.delete():
      result.message = f"Deleted prompt: {name}"
    else:
      result = Result.fail(f"Failed to delete prompt: {name}")

    return result