"""
Model command class for the CLAIA CLI.

This module contains the command class for listing and selecting models.
Delegates to cli.model_* tools via the registry.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.lib.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)


class ModelCommand(BaseCommand):
  """Command to list and select models. Delegates to cli.model_* tools."""
  
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
  
  def _get_tool_params(self) -> Dict[str, Any]:
    """Get common parameters to pass to cli tools."""
    return {
      'active_model': self.settings.active_model,
      'active_model_source': getattr(self.settings, 'active_model_source', None),
      'default_model': self.settings.default_model,
      'registry': self.registry,
    }
  
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
    List all available models via cli.model_list tool.
    
    Args:
        args: Optional filter arguments
    
    Returns:
        Result with list of models
    """
    params = self._get_tool_params()
    if args:
      params['filter'] = ' '.join(args)
    
    return self.registry.run_command('cli.model_list', params, None)
  
  def _show_current(self) -> Result:
    """Show information about the current active model via cli.model_current tool."""
    params = self._get_tool_params()
    return self.registry.run_command('cli.model_current', params, None)
  
  def _show_model(self, args: List[str]) -> Result:
    """
    Show detailed information about a specific model via cli.model_show tool.
    
    Args:
        args: List containing model name
    
    Returns:
        Result with model details
    """
    if not args:
      output = f"Missing model name. Usage: {self.format_command('model show <name>')}"
      return Result(success=False, message=output)
    
    params = self._get_tool_params()
    params['model_name'] = args[0]
    
    return self.registry.run_command('cli.model_show', params, None)
  
  def _select_model(self, args: List[str]) -> Result:
    """
    Select a model as the active model.
    
    Note: This method modifies settings directly rather than delegating to a tool,
    since it needs to update the local settings object.
    
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
      
      # First, try to resolve as an alias
      resolved_name = self._resolve_model_alias(model_name, models)
      
      if resolved_name:
        # Alias was resolved to a canonical name
        if resolved_name != model_name:
          self.logger.info(f"Resolved alias '{model_name}' to canonical name '{resolved_name}'")
          print(f"\nNote: '{model_name}' is an alias for '{resolved_name}'")
        actual_model_name = resolved_name
      elif model_name not in models:
        # Model not found in definitions - offer to use it anyway
        print(f"\nWarning: Model '{model_name}' is not in the definitions.")
        print("This model may still work if supported by the provider/deployment,")
        print("but CLAIA cannot verify its existence or capabilities.")
        
        try:
          response = input("\nDo you want to use this model anyway? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
          return Result(success=False, message="\nModel selection cancelled.")
        
        if response not in ['y', 'yes']:
          output = f"\nModel selection cancelled."
          output += f"\nUse {self.format_command('model list')} to see available models."
          return Result(success=False, message=output)
        
        # User confirmed - use the model name as-is
        actual_model_name = model_name
      else:
        # Direct match found
        actual_model_name = model_name
      
      # Set the active model (runtime only, not persisted)
      old_model = self.settings.active_model
      self.settings.active_model = actual_model_name
      self.settings.active_model_source = "cli"
      
      output = f"\nActive model changed: {old_model or 'None'} → {actual_model_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: {self.format_command(f'set default_model {actual_model_name}')}"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error selecting model '{model_name}': {str(e)}"
      self.logger.error(f"Error selecting model: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _resolve_model_alias(self, model_name: str, models: Dict[str, Any]) -> Optional[str]:
    """
    Resolve a model name or alias to its canonical name.
    
    Args:
        model_name: Name or alias to resolve
        models: Dictionary of available models
    
    Returns:
        Canonical model name if found, None otherwise
    """
    # Check if it's already a canonical name
    if model_name in models:
      return model_name
    
    # Check aliases
    for canonical_name, model_def in models.items():
      if hasattr(model_def, 'aliases') and model_def.aliases and model_name in model_def.aliases:
        self.logger.debug(f"Resolved alias '{model_name}' to '{canonical_name}'")
        return canonical_name
    
    # Not found
    return None

