"""
This module contains commands for managing models.
"""

# External dependencies
import os
import json
import logging
from typing import List, Dict, Any, Optional

# Internal Dependencies
from .base import Command, command
from results import Result
from settings import Settings
from models import model_definitions, model_sources



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
  def list_models(self, settings: Settings, model_name: str = "") -> Result:
    """List all models or details about a specific model"""
    result = Result()

    if model_name:
      # Get available sources for this model
      available_sources = []
      for s in model_sources.keys():
        if s in model_definitions.get(model_name, {}).get('sources', []):
          available_sources.append(s)

      if model_name in model_definitions and available_sources:
        model_info = model_definitions[model_name]
        output = [
          f"Name: {model_name}",
          f"Title: {model_info['title']}",
          f"Description: {model_info['description']}",
          f"Available Sources: {', '.join(available_sources)}"
        ]

        if "training_data" in model_info:
          output.append(f"Training Data: {model_info['training_data']}")
        if "capabilities" in model_info:
          capabilities = [c.value for c in model_info['capabilities']]
          output.append(f"Capabilities: {', '.join(capabilities)}")

        result.data = model_info
        result.message = "\n".join(output)
        return result
      else:
        return Result.fail(f"Model with name {model_name} not found or has no available sources")
    else:
      # Filter models to only those with available sources
      available_models = {
        name: model for name, model in model_definitions.items()
        if any(s in model.get('sources', []) for s in model_sources.keys())
      }

      if not available_models:
        result.message = "No models available with configured sources"
        return result

      # Get max model name length for padding
      max_name_length = max(len(name) for name in available_models.keys())

      output = []
      model_list = []
      for model_name in available_models.keys():
        # Get available sources for this model
        available_sources = []
        for s in model_sources.keys():
          if s in model_definitions.get(model_name, {}).get('sources', []):
            available_sources.append(s)
        sources_str = f" ({', '.join(available_sources)})"

        # Add model name padded to align sources
        output.append(f"{model_name:<{max_name_length}}{sources_str}")
        model_list.append({
          "name": model_name,
          "sources": available_sources,
          "info": available_models[model_name]
        })

      result.data = model_list
      result.message = "\n".join(output)
      return result

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
  def set_model(self, settings: Settings, model_name: str, source: str = None) -> Result:
    """Set the model to use for generation"""
    result = Result()

    # Handle known models in definitions
    if model_name in model_definitions:
      # Get available sources for this model
      available_sources = []
      for s in model_sources.keys():
        if s in model_definitions.get(model_name, {}).get('sources', []):
          available_sources.append(s)

      if available_sources:
        if source:
          if source not in available_sources:
            return Result.fail(f"Invalid source '{source}' for model '{model_name}'. Available sources: {', '.join(available_sources)}")
          chosen_source = source
        else:
          chosen_source = available_sources[0]

        settings.active_model = model_name
        settings.active_model_source = chosen_source
        result.message = f"Model set to {model_name} using source {chosen_source}"
        return result
      else:
        # Model exists in definitions but has no available sources
        warning = f"Model '{model_name}' exists in definitions but has no available sources."
        logger.warning(warning)
    else:
      # Model not found in definitions, guess source based on name format
      warning = f"Model '{model_name}' not found in definitions. Will attempt to use directly."
      logger.warning(warning)

    # For unknown models or models without sources, make a best guess
    if source:
      if source in model_sources.keys():
        chosen_source = source
      else:
        return Result.fail(f"Invalid source '{source}'. Available sources: {', '.join(model_sources.keys())}")
    else:
      # Default to transformers source for unknown models, especially if it has a slash
      # which likely indicates a HuggingFace model ID
      if "/" in model_name:
        chosen_source = "transformers"
      else:
        chosen_source = "transformers"  # Default fallback

    settings.active_model = model_name
    settings.active_model_source = chosen_source

    result.message = f"Model set to {model_name} using source {chosen_source} (unregistered model, will attempt direct loading)"
    return result

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
  def current_model(self, settings: Settings) -> Result:
    """Print currently selected model"""
    result = Result()

    if settings.active_model:
      source_str = f" ({settings.active_model_source})" if settings.active_model_source else ""
      result.message = f"Current model: {settings.active_model}{source_str}"
    else:
      result.message = "No model selected"

    return result

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
  def print_model(self, settings: Settings) -> Result:
    """Alias for current_model"""
    return self.current_model(settings)



########################################################################
#                            VLLM COMMANDS                             #
########################################################################

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
  def print_vllm_zone(self, settings: Settings) -> Result:
    """Display the current VLLM zone"""
    result = Result()

    if settings.vllm_zone:
      result.message = f"Current VLLM zone: {settings.vllm_zone}"
    else:
      result.message = "No VLLM zone set"

    return result

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
  def set_vllm_zone(self, settings: Settings, zone: str) -> Result:
    """Set the VLLM zone"""
    result = Result()

    settings.vllm_zone = zone
    result.message = f"VLLM zone set to: {zone}"

    return result

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
  def print_vllm_email(self, settings: Settings) -> Result:
    """Display the current VLLM email"""
    result = Result()

    if settings.vllm_email:
      result.message = f"Current VLLM email: {settings.vllm_email}"
    else:
      result.message = "No VLLM email set"

    return result

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
  def set_vllm_email(self, settings: Settings, email: str) -> Result:
    """Set the VLLM email"""
    result = Result()

    settings.vllm_email = email
    result.message = f"VLLM email set to: {email}"

    return result

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
  def print_vllm_subdomain(self, settings: Settings) -> Result:
    """Display the current VLLM subdomain"""
    result = Result()

    if settings.vllm_subdomain:
      result.message = f"Current VLLM subdomain: {settings.vllm_subdomain}"
    else:
      result.message = "No VLLM subdomain set"

    return result

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
  def set_vllm_subdomain(self, settings: Settings, subdomain: str) -> Result:
    """Set the VLLM subdomain"""
    result = Result()

    settings.vllm_subdomain = subdomain
    result.message = f"VLLM subdomain set to: {subdomain}"

    return result
