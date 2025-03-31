# External dependencies
import os
import json
import logging
from typing import List, Dict, Any, Optional

# Internal Dependencies
from commands.base import Command, command
from settings import Settings
from models import definitions, sources



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class ModelCommand(Command):

  @command(
    path=["list"],
    description="List available models",
    help_text="List all available models or details about a specific model",
    parameters={
      "type": "object",
      "properties": {
        "model_name": {
          "type": "string",
          "description": "Name of the model to get details for (optional)"
        }
      }
    },
    returns={
      "type": "string",
      "description": "List of models or details about a specific model"
    },
    ai_callable=True
  )
  def list_models(self, settings: Settings, model_name: str = "") -> str:
    """List the available models or details about a specific model"""
    result = []

    if model_name:
      # Get available sources for this model
      available_sources = []
      for s in sources.keys():
        if s in definitions.get(model_name, {}).get('sources', []):
          available_sources.append(s)

      if model_name in definitions and available_sources:
        model_info = definitions[model_name]
        result.append(f"Name: {model_name}")
        result.append(f"Title: {model_info['title']}")
        result.append(f"Description: {model_info['description']}")
        result.append(f"Available Sources: {', '.join(available_sources)}")

        if "training_data" in model_info:
          result.append(f"Training Data: {model_info['training_data']}")
        if "capabilities" in model_info:
          capabilities = [c.value for c in model_info['capabilities']]
          result.append(f"Capabilities: {', '.join(capabilities)}")
      else:
        result.append(f"Model with name {model_name} not found or has no available sources")
    else:
      # Filter models to only those with available sources
      available_models = {
        name: model for name, model in definitions.items()
        if any(s in model.get('sources', []) for s in sources.keys())
      }

      if not available_models:
        result.append("No models available with configured sources")
        return "\n".join(result)

      # Get max model name length for padding
      max_name_length = max(len(name) for name in available_models.keys())

      for model_name in available_models.keys():
        # Get available sources for this model
        available_sources = []
        for s in sources.keys():
          if s in definitions.get(model_name, {}).get('sources', []):
            available_sources.append(s)
        sources_str = f" ({', '.join(available_sources)})"

        # Add model name padded to align sources
        result.append(f"{model_name:<{max_name_length}}{sources_str}")

    # Print to console and return as string for function calling
    output = "\n".join(result)
    print(output)
    return output

  @command(
    path=["set"],
    description="Set the current model to use for generation",
    help_text="Select a model to use for generation",
    parameters={
      "type": "object",
      "properties": {
        "model_name": {
          "type": "string",
          "description": "Name of the model to use"
        },
        "source": {
          "type": "string",
          "description": "Source to use for the model (optional)"
        }
      },
      "required": ["model_name"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_model(self, settings: Settings, model_name: str, source: str = None) -> str:
    """Set the selected model"""
    # Get available sources for this model
    available_sources = []
    for s in sources.keys():
      if s in definitions.get(model_name, {}).get('sources', []):
        available_sources.append(s)

    if model_name not in definitions or not available_sources:
      msg = f"Model '{model_name}' not found or has no available sources"
      print(msg)
      return msg

    if source:
      if source not in available_sources:
        msg = f"Invalid source '{source}' for model '{model_name}'. Available sources: {', '.join(available_sources)}"
        print(msg)
        return msg
      chosen_source = source
    else:
      chosen_source = available_sources[0]

    settings.active_model = model_name
    settings.active_model_source = chosen_source
    settings.save()

    msg = f"Model set to {model_name} using source {chosen_source}"
    print(msg)
    return msg

  @command(
    path=["current"],
    description="Display the current model selection",
    help_text="Display the current model selection",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current model information"
    },
    ai_callable=True
  )
  def current_model(self, settings: Settings) -> str:
    """Print currently selected model"""
    if settings.active_model:
      source_str = f" ({settings.active_model_source})" if settings.active_model_source else ""
      msg = f"Current model: {settings.active_model}{source_str}"
      print(msg)
      return msg
    else:
      msg = "No model selected"
      print(msg)
      return msg

  @command(
    path=["print"],
    description="Display the current model selection",
    help_text="Display the current model selection (alias for 'current')",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current model information"
    },
    ai_callable=True
  )
  def print_model(self, settings: Settings) -> str:
    """Alias for current_model"""
    return self.current_model(settings)



  ##################################################
  #                  VLLM COMMANDS                 #
  ##################################################

  @command(
    path=["vllm", "zone"],
    description="Display the current VLLM zone",
    help_text="Display the current VLLM zone",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current VLLM zone"
    },
    ai_callable=True
  )
  def print_vllm_zone(self, settings: Settings) -> str:
    """Display the current VLLM zone"""
    if settings.vllm_zone:
      msg = f"Current VLLM zone: {settings.vllm_zone}"
      print(msg)
      return msg
    else:
      msg = "No VLLM zone set"
      print(msg)
      return msg

  @command(
    path=["vllm", "zone", "set"],
    description="Set the VLLM zone",
    help_text="Set the VLLM zone (e.g., example.com)",
    parameters={
      "type": "object",
      "properties": {
        "zone": {
          "type": "string",
          "description": "Zone to set (e.g., example.com)"
        }
      },
      "required": ["zone"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_vllm_zone(self, settings: Settings, zone: str) -> str:
    """Set the VLLM zone"""
    settings.vllm_zone = zone
    msg = f"VLLM zone set to: {zone}"
    print(msg)
    return msg

  @command(
    path=["vllm", "email"],
    description="Display the current VLLM email",
    help_text="Display the current VLLM email",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current VLLM email"
    },
    ai_callable=True
  )
  def print_vllm_email(self, settings: Settings) -> str:
    """Display the current VLLM email"""
    if settings.vllm_email:
      msg = f"Current VLLM email: {settings.vllm_email}"
      print(msg)
      return msg
    else:
      msg = "No VLLM email set"
      print(msg)
      return msg

  @command(
    path=["vllm", "email", "set"],
    description="Set the VLLM email",
    help_text="Set the VLLM email (used for SSL certificates)",
    parameters={
      "type": "object",
      "properties": {
        "email": {
          "type": "string",
          "description": "Email to set (used for SSL certificates)"
        }
      },
      "required": ["email"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_vllm_email(self, settings: Settings, email: str) -> str:
    """Set the VLLM email"""
    settings.vllm_email = email
    msg = f"VLLM email set to: {email}"
    print(msg)
    return msg

  @command(
    path=["vllm", "subdomain"],
    description="Display the current VLLM subdomain",
    help_text="Display the current VLLM subdomain",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current VLLM subdomain"
    },
    ai_callable=True
  )
  def print_vllm_subdomain(self, settings: Settings) -> str:
    """Display the current VLLM subdomain"""
    if settings.vllm_subdomain:
      msg = f"Current VLLM subdomain: {settings.vllm_subdomain}"
      print(msg)
      return msg
    else:
      msg = "No VLLM subdomain set"
      print(msg)
      return msg

  @command(
    path=["vllm", "subdomain", "set"],
    description="Set the VLLM subdomain",
    help_text="Set the VLLM subdomain (e.g., vllm)",
    parameters={
      "type": "object",
      "properties": {
        "subdomain": {
          "type": "string",
          "description": "Subdomain to set (e.g., vllm)"
        }
      },
      "required": ["subdomain"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_vllm_subdomain(self, settings: Settings, subdomain: str) -> str:
    """Set the VLLM subdomain"""
    settings.vllm_subdomain = subdomain
    msg = f"VLLM subdomain set to: {subdomain}"
    print(msg)
    return msg
