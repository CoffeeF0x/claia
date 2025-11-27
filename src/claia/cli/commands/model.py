"""
Model command for listing and selecting models.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.lib.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)


class ModelCommand(BaseCommand):
  """Command to list and select models."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute model command: show usage or route to subcommand."""
    if not args:
      return self._show_usage()
    
    subcommand = args[0].lower()
    handlers = {
      'list': lambda: self._list_models(args[1:]),
      'show': lambda: self._show_model(args[1:]),
      'info': lambda: self._show_model(args[1:]),
      'select': lambda: self._select_model(args[1:]),
      'current': self._show_current,
    }
    
    handler = handlers.get(subcommand)
    return handler() if handler else self._select_model(args)
  
  def _get_tool_params(self) -> Dict[str, Any]:
    """Get common parameters for cli tools."""
    return {
      'active_model': self.settings.active_model,
      'active_model_source': getattr(self.settings, 'active_model_source', None),
      'default_model': self.settings.default_model,
      'registry': self.registry,
    }
  
  def _show_usage(self) -> Result:
    """Show usage information and current model."""
    prefix = self.get_help_prefix()
    
    lines = []
    if self.settings.active_model:
      lines.append(f"\nActive model: {self.settings.active_model}")
      if self.settings.active_model_source:
        lines.append(f"  Source: {self.settings.active_model_source}")
    else:
      lines.append("\nNo active model")
    
    lines.append(f"Default model (from settings): {self.settings.default_model or 'None'}")
    lines.extend([
      "\nUsage:",
      f"  {prefix}model list [filter]         - List all available models (optionally filter)",
      f"  {prefix}model current               - Show current active model",
      f"  {prefix}model show <name>           - Show detailed info about a model",
      f"  {prefix}model select <name>         - Select a model as active",
      f"  {prefix}model <name>                - Shorthand for select",
    ])
    return Result(success=True, data="\n".join(lines))
  
  def _list_models(self, args: List[str]) -> Result:
    """List all available models."""
    params = self._get_tool_params()
    if args:
      params['filter'] = ' '.join(args)
    return self.registry.run_command('cli.model_list', params, None)
  
  def _show_current(self) -> Result:
    """Show current active model info."""
    return self.registry.run_command('cli.model_current', self._get_tool_params(), None)
  
  def _show_model(self, args: List[str]) -> Result:
    """Show detailed info about a model."""
    if not args:
      return Result(success=False, message=f"Missing model name. Usage: {self.format_command('model show <name>')}")
    
    params = self._get_tool_params()
    params['model_name'] = args[0]
    return self.registry.run_command('cli.model_show', params, None)
  
  def _select_model(self, args: List[str]) -> Result:
    """Select a model as the active model."""
    if not args:
      return Result(success=False, message=f"Missing model name. Usage: {self.format_command('model select <name>')}")
    
    model_name = args[0]
    
    try:
      models = self.registry.get_supported_models()
      resolved = self._resolve_alias(model_name, models)
      
      if resolved:
        if resolved != model_name:
          print(f"\nNote: '{model_name}' is an alias for '{resolved}'")
        actual_name = resolved
      elif model_name not in models:
        # Warn about unknown model
        print(f"\nWarning: Model '{model_name}' is not in the definitions.")
        print("This model may still work if supported by the provider/deployment,")
        print("but CLAIA cannot verify its existence or capabilities.")
        
        try:
          response = input("\nDo you want to use this model anyway? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
          return Result(success=False, message="\nModel selection cancelled.")
        
        if response not in ['y', 'yes']:
          return Result(success=False, message=f"\nModel selection cancelled.\nUse {self.format_command('model list')} to see available models.")
        
        actual_name = model_name
      else:
        actual_name = model_name
      
      old_model = self.settings.active_model
      self.settings.active_model = actual_name
      self.settings.active_model_source = "cli"
      
      output = f"\nActive model changed: {old_model or 'None'} → {actual_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: {self.format_command(f'set default_model {actual_name}')}"
      return Result(success=True, data=output)
      
    except Exception as e:
      self.logger.error(f"Error selecting model: {e}", exc_info=True)
      return Result(success=False, message=f"Error selecting model '{model_name}': {str(e)}")
  
  def _resolve_alias(self, model_name: str, models: Dict[str, Any]) -> Optional[str]:
    """Resolve a model name or alias to its canonical name."""
    if model_name in models:
      return model_name
    
    for canonical, model_def in models.items():
      if hasattr(model_def, 'aliases') and model_def.aliases and model_name in model_def.aliases:
        return canonical
    
    return None
