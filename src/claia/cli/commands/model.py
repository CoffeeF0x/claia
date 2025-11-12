"""
Model command class for the CLAIA CLI.

This module contains the command class for listing and selecting models.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.lib.results import Result
from claia.hooks import ModelDefinition
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Constants for formatted output
MODEL_DIVIDER = "-" * 70


class ModelCommand(BaseCommand):
  """Command to list and select models."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the model command.
    
    Args:
        args: List of arguments (subcommand and additional args)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result indicating success/failure
    """
    self.logger.debug("Model command received")
    
    # If no args, show usage and current model
    if not args:
      return self._show_usage()
    
    subcommand = args[0].lower()
    
    # Route to appropriate subcommand handler
    handlers = {
      'list': lambda: self._list_models(args[1:]),
      'show': lambda: self._show_model(args[1:]),
      'select': lambda: self._select_model(args[1:]),
      'info': lambda: self._show_model(args[1:]),  # alias for show
      'current': self._show_current,
    }
    
    handler = handlers.get(subcommand)
    if handler:
      return handler()
    else:
      # If not a subcommand, treat as model name to select
      return self._select_model(args)
  
  def _show_usage(self) -> Result:
    """Show usage information and current model."""
    output_lines = []
    
    if self.settings.active_model:
      output_lines.append(f"\nActive model: {self.settings.active_model}")
      if self.settings.active_model_source:
        output_lines.append(f"  Source: {self.settings.active_model_source}")
    else:
      output_lines.append("\nNo active model")
    
    default_model = self.settings.default_model or "None"
    output_lines.append(f"Default model (from settings): {default_model}")
    
    output_lines.append("\nUsage:")
    prefix = self.get_help_prefix()
    
    output_lines.append(f"  {prefix}model list [filter]         - List all available models (optionally filter)")
    output_lines.append(f"  {prefix}model current               - Show current active model")
    output_lines.append(f"  {prefix}model show <name>           - Show detailed info about a model")
    output_lines.append(f"  {prefix}model select <name>         - Select a model as active")
    output_lines.append(f"  {prefix}model <name>                - Shorthand for select")
    
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _list_models(self, args: List[str]) -> Result:
    """
    List all available models.
    
    Args:
        args: Optional filter arguments
    
    Returns:
        Result with list of models
    """
    try:
      models = self.registry.get_supported_models()
      
      if not models:
        return Result(success=True, data="No models available.")
      
      # Apply filter if provided
      filter_text = ' '.join(args).lower() if args else None
      
      output_lines = []
      output_lines.append("\nAvailable models:")
      output_lines.append(MODEL_DIVIDER)
      
      # Sort models by company and then name
      sorted_models = sorted(
        models.items(),
        key=lambda x: (x[1].company or 'Unknown', x[0])
      )
      
      current_company = None
      model_count = 0
      
      for model_name, model_def in sorted_models:
        # Apply filter
        if filter_text:
          searchable = f"{model_name} {model_def.title or ''} {model_def.company or ''} {model_def.description or ''}".lower()
          if filter_text not in searchable:
            continue
        
        # Group by company
        if model_def.company != current_company:
          if current_company is not None:
            output_lines.append("")
          current_company = model_def.company
          output_lines.append(f"\n{current_company or 'Other'}:")
          output_lines.append("-" * 40)
        
        # Mark the current active model
        marker = " (active)" if model_name == self.settings.active_model else ""
        marker += " (default)" if model_name == self.settings.default_model else ""
        
        # Build model line
        title = model_def.title or model_name
        line = f"  • {model_name}{marker}"
        if title != model_name:
          line += f" - {title}"
        
        output_lines.append(line)
        
        # Add description if available
        if model_def.description:
          desc_preview = model_def.description[:80]
          if len(model_def.description) > 80:
            desc_preview += "..."
          output_lines.append(f"    {desc_preview}")
        
        # Add key metadata on one line
        meta_parts = []
        if model_def.parameters:
          meta_parts.append(f"Size: {model_def.parameters}")
        if model_def.context_length:
          context_kb = model_def.context_length / 1000
          meta_parts.append(f"Context: {context_kb:.0f}k")
        if model_def.capabilities:
          meta_parts.append(f"Capabilities: {', '.join(model_def.capabilities[:3])}")
        
        if meta_parts:
          output_lines.append(f"    {' | '.join(meta_parts)}")
        
        model_count += 1
      
      if model_count == 0:
        output_lines.append(f"\nNo models matching filter: {filter_text}")
      else:
        output_lines.append("")
        output_lines.append(f"Total: {model_count} model(s)")
      
      output_lines.append("")
      output = "\n".join(output_lines)
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error listing models: {str(e)}"
      self.logger.error(f"Error listing models: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _show_current(self) -> Result:
    """Show information about the current active model."""
    if not self.settings.active_model:
      return Result(success=True, data="No active model selected.")
    
    # Get model definition
    try:
      models = self.registry.get_supported_models()
      model_def = models.get(self.settings.active_model)
      
      if not model_def:
        output = f"\nActive model: {self.settings.active_model}"
        if self.settings.active_model_source:
          output += f"\nSource: {self.settings.active_model_source}"
        output += "\n(No additional information available)"
        return Result(success=True, data=output)
      
      return self._format_model_details(self.settings.active_model, model_def)
      
    except Exception as e:
      output = f"Error getting model info: {str(e)}"
      self.logger.error(f"Error getting model info: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _show_model(self, args: List[str]) -> Result:
    """
    Show detailed information about a specific model.
    
    Args:
        args: List containing model name
    
    Returns:
        Result with model details
    """
    if not args:
      output = f"Missing model name. Usage: {self.format_command('model show <name>')}"
      return Result(success=False, message=output)
    
    model_name = args[0]
    
    try:
      models = self.registry.get_supported_models()
      model_def = models.get(model_name)
      
      if not model_def:
        output = f"Model not found: {model_name}\n"
        output += f"Use {self.format_command('model list')} to see available models."
        return Result(success=False, message=output)
      
      return self._format_model_details(model_name, model_def)
      
    except Exception as e:
      output = f"Error getting model info for '{model_name}': {str(e)}"
      self.logger.error(f"Error getting model info: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _format_model_details(self, model_name: str, model_def: ModelDefinition) -> Result:
    """
    Format detailed model information.
    
    Args:
        model_name: Name of the model
        model_def: Model definition
    
    Returns:
        Result with formatted details
    """
    output_lines = []
    output_lines.append(f"\nModel: {model_name}")
    output_lines.append(MODEL_DIVIDER)
    
    if model_def.title:
      output_lines.append(f"Title: {model_def.title}")
    
    if model_def.company:
      output_lines.append(f"Company: {model_def.company}")
    
    if model_def.description:
      output_lines.append(f"\nDescription:")
      output_lines.append(f"  {model_def.description}")
    
    if model_def.parameters:
      output_lines.append(f"\nParameters: {model_def.parameters}")
    
    if model_def.context_length:
      output_lines.append(f"Context Length: {model_def.context_length:,} tokens")
    
    if model_def.capabilities:
      output_lines.append(f"Capabilities: {', '.join(model_def.capabilities)}")
    
    if model_def.aliases:
      output_lines.append(f"\nAliases: {', '.join(model_def.aliases)}")
    
    if model_def.deployments:
      output_lines.append(f"\nSupported Deployments: {', '.join(model_def.deployments)}")
    
    if model_def.architectures:
      output_lines.append(f"Architectures: {', '.join(model_def.architectures)}")
    
    if model_def.license:
      output_lines.append(f"\nLicense: {model_def.license}")
    
    if model_def.url:
      output_lines.append(f"URL: {model_def.url}")
    
    if model_def.identifiers:
      output_lines.append(f"\nIdentifiers:")
      for arch, identifier in model_def.identifiers.items():
        output_lines.append(f"  {arch}: {identifier}")
    
    output_lines.append("")
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _select_model(self, args: List[str]) -> Result:
    """
    Select a model as the active model.
    
    Args:
        args: List containing model name
    
    Returns:
        Result indicating success/failure
    """
    if not args:
      output = f"Missing model name. Usage: {self.format_command('model select <name>')}"
      return Result(success=False, message=output)
    
    model_name = args[0]
    
    try:
      # Verify the model exists
      models = self.registry.get_supported_models()
      
      if model_name not in models:
        output = f"Model not found: {model_name}\n"
        output += f"Use {self.format_command('model list')} to see available models."
        return Result(success=False, message=output)
      
      # Set the active model (runtime only, not persisted)
      old_model = self.settings.active_model
      self.settings.active_model = model_name
      self.settings.active_model_source = "cli"
      
      output = f"\nActive model changed: {old_model or 'None'} → {model_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: {self.format_command(f'set default_model {model_name}')}"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error selecting model '{model_name}': {str(e)}"
      self.logger.error(f"Error selecting model: {e}", exc_info=True)
      return Result(success=False, message=output)

