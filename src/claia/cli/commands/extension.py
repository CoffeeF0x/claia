"""
CLI command module providing CLI-accessible tools for models, agents, prompts, conversations, and settings.

This module exposes all CLI functionality as tools that can be invoked via:
- Direct tool calls: :tool cli.model_list
- CLI commands: :model list (which delegate to these tools)
"""

import sys
import time
import logging
import importlib.metadata as importlib_metadata
from typing import Dict, Any, Optional, List
from collections import defaultdict
import pluggy

from claia.hooks.tool import ToolModuleInfo, ToolDefinition, ArgumentDefinition
from claia.lib.results import Result
from claia.lib.data.models import Conversation, Prompt
from claia.cli.storage import JsonStore
from claia.lib.enums.conversation import MessageRole


hookimpl = pluggy.HookimplMarker("claia_tool_modules")
logger = logging.getLogger(__name__)


# Constants
DIVIDER = "-" * 70


class CLIModulePlugin:
  """CLI module implementing tools for models, agents, prompts, conversations, and settings."""

  @hookimpl
  def get_module_info(self) -> ToolModuleInfo:
    return ToolModuleInfo(
      name="cli",
      title="CLI Tools",
      description="Model, agent, prompt, conversation, and settings management tools",
    )

  @hookimpl
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    """Return all available tools in this module."""
    return {
      # Model tools
      "model_list": ToolDefinition(
        name="model_list",
        description="List all available models, optionally filtered",
        callable=self._model_list,
        arguments={
          "filter": ArgumentDefinition(
            name="filter",
            description="Optional filter text to search models",
            data_type="str",
            required=False
          ),
          "active_model": ArgumentDefinition(
            name="active_model",
            description="Current active model name",
            data_type="str",
            required=False
          ),
          "default_model": ArgumentDefinition(
            name="default_model",
            description="Default model name from settings",
            data_type="str",
            required=False
          ),
          "registry": ArgumentDefinition(
            name="registry",
            description="Registry instance (injected)",
            data_type="custom",
            required=False
          ),
        }
      ),
      "model_show": ToolDefinition(
        name="model_show",
        description="Show detailed information about a specific model",
        callable=self._model_show,
        arguments={
          "model_name": ArgumentDefinition(
            name="model_name",
            description="Name or alias of the model to show",
            data_type="str",
            required=True
          ),
          "registry": ArgumentDefinition(
            name="registry",
            description="Registry instance (injected)",
            data_type="custom",
            required=False
          ),
        }
      ),
      "model_current": ToolDefinition(
        name="model_current",
        description="Show information about the current active model",
        callable=self._model_current,
        arguments={
          "active_model": ArgumentDefinition(
            name="active_model",
            description="Current active model name",
            data_type="str",
            required=False
          ),
          "active_model_source": ArgumentDefinition(
            name="active_model_source",
            description="Source of active model selection",
            data_type="str",
            required=False
          ),
          "registry": ArgumentDefinition(
            name="registry",
            description="Registry instance (injected)",
            data_type="custom",
            required=False
          ),
        }
      ),

      # Agent tools
      "agent_list": ToolDefinition(
        name="agent_list",
        description="List all available agents",
        callable=self._agent_list,
        arguments={
          "active_agent": ArgumentDefinition(
            name="active_agent",
            description="Current active agent name",
            data_type="str",
            required=False
          ),
          "default_agent": ArgumentDefinition(
            name="default_agent",
            description="Default agent name from settings",
            data_type="str",
            required=False
          ),
          "registry": ArgumentDefinition(
            name="registry",
            description="Registry instance (injected)",
            data_type="custom",
            required=False
          ),
        }
      ),
      "agent_current": ToolDefinition(
        name="agent_current",
        description="Show the current active agent",
        callable=self._agent_current,
        arguments={
          "active_agent": ArgumentDefinition(
            name="active_agent",
            description="Current active agent name",
            data_type="str",
            required=False
          ),
          "default_agent": ArgumentDefinition(
            name="default_agent",
            description="Default agent name from settings",
            data_type="str",
            required=False
          ),
        }
      ),

      # Prompt tools
      "prompt_list": ToolDefinition(
        name="prompt_list",
        description="List all available prompts",
        callable=self._prompt_list,
        arguments={
          "files_directory": ArgumentDefinition(
            name="files_directory",
            description="Files directory path",
            data_type="str",
            required=True
          ),
          "active_prompt_name": ArgumentDefinition(
            name="active_prompt_name",
            description="Name of the active prompt",
            data_type="str",
            required=False
          ),
          "default_prompt": ArgumentDefinition(
            name="default_prompt",
            description="Default prompt name from settings",
            data_type="str",
            required=False
          ),
        }
      ),
      "prompt_print": ToolDefinition(
        name="prompt_print",
        description="Print the content of a prompt",
        callable=self._prompt_print,
        arguments={
          "prompt_name": ArgumentDefinition(
            name="prompt_name",
            description="Name of the prompt to print (empty for active)",
            data_type="str",
            required=False
          ),
          "files_directory": ArgumentDefinition(
            name="files_directory",
            description="Files directory path",
            data_type="str",
            required=True
          ),
          "active_prompt_name": ArgumentDefinition(
            name="active_prompt_name",
            description="Name of the active prompt",
            data_type="str",
            required=False
          ),
        }
      ),

      # Conversation tools
      "conversation_list": ToolDefinition(
        name="conversation_list",
        description="List all saved conversations",
        callable=self._conversation_list,
        arguments={
          "files_directory": ArgumentDefinition(
            name="files_directory",
            description="Files directory path",
            data_type="str",
            required=True
          ),
          "active_conversation_id": ArgumentDefinition(
            name="active_conversation_id",
            description="ID of the active conversation",
            data_type="str",
            required=False
          ),
        }
      ),
      "conversation_print": ToolDefinition(
        name="conversation_print",
        description="Print the entire active conversation",
        callable=self._conversation_print,
        arguments={
          "conversation": ArgumentDefinition(
            name="conversation",
            description="Conversation object to print",
            data_type="custom",
            required=False
          ),
        }
      ),
      "conversation_details": ToolDefinition(
        name="conversation_details",
        description="Show metadata and technical info about the active conversation",
        callable=self._conversation_details,
        arguments={
          "conversation": ArgumentDefinition(
            name="conversation",
            description="Conversation object to show details for",
            data_type="custom",
            required=False
          ),
        }
      ),

      # Settings tools
      "settings_get": ToolDefinition(
        name="settings_get",
        description="Get the value of a setting or all settings",
        callable=self._settings_get,
        arguments={
          "setting_name": ArgumentDefinition(
            name="setting_name",
            description="Name of the setting to get (empty for all)",
            data_type="str",
            required=False
          ),
          "settings": ArgumentDefinition(
            name="settings",
            description="Settings object (injected)",
            data_type="custom",
            required=False
          ),
        }
      ),

      # System tools
      "version": ToolDefinition(
        name="version",
        description="Show CLAIA version information",
        callable=self._version,
        arguments={}
      ),
      "help": ToolDefinition(
        name="help",
        description="Show help information",
        callable=self._help,
        arguments={
          "registry": ArgumentDefinition(
            name="registry",
            description="Registry instance (injected)",
            data_type="custom",
            required=False
          ),
          "command_specs": ArgumentDefinition(
            name="command_specs",
            description="Command specifications for help display",
            data_type="custom",
            required=False
          ),
          "current_mode": ArgumentDefinition(
            name="current_mode",
            description="Current mode (interactive or cli)",
            data_type="str",
            required=False,
            default_value="interactive"
          ),
        }
      ),
    }

  # ======================================================================
  # Model Tools
  # ======================================================================
  def _model_list(self, filter: str = None, active_model: str = None, 
                  default_model: str = None, registry=None, **kwargs) -> str:
    """List all available models."""
    if not registry:
      return "Error: Registry not available"
    
    try:
      models = registry.get_supported_models()
      
      if not models:
        return "No models available."
      
      filter_text = filter.lower() if filter else None
      
      output_lines = []
      output_lines.append("\nAvailable models:")
      output_lines.append(DIVIDER)
      
      # Sort models by company and then name
      sorted_models = sorted(
        models.items(),
        key=lambda x: (getattr(x[1], 'company', None) or 'Unknown', x[0])
      )
      
      current_company = None
      model_count = 0
      
      for model_name, model_def in sorted_models:
        # Apply filter
        if filter_text:
          searchable = f"{model_name} {getattr(model_def, 'title', '') or ''} {getattr(model_def, 'company', '') or ''} {getattr(model_def, 'description', '') or ''}".lower()
          if filter_text not in searchable:
            continue
        
        # Group by company
        company = getattr(model_def, 'company', None)
        if company != current_company:
          if current_company is not None:
            output_lines.append("")
          current_company = company
          output_lines.append(f"\n{current_company or 'Other'}:")
          output_lines.append("-" * 40)
        
        # Mark the current active model
        marker = " (active)" if model_name == active_model else ""
        marker += " (default)" if model_name == default_model else ""
        
        # Build model line
        title = getattr(model_def, 'title', None) or model_name
        line = f"  • {model_name}{marker}"
        if title != model_name:
          line += f" - {title}"
        
        output_lines.append(line)
        
        # Add description if available
        description = getattr(model_def, 'description', None)
        if description:
          desc_preview = description[:80]
          if len(description) > 80:
            desc_preview += "..."
          output_lines.append(f"    {desc_preview}")
        
        # Add key metadata on one line
        meta_parts = []
        parameters = getattr(model_def, 'parameters', None)
        context_length = getattr(model_def, 'context_length', None)
        capabilities = getattr(model_def, 'capabilities', None)
        
        if parameters:
          meta_parts.append(f"Size: {parameters}")
        if context_length:
          context_kb = context_length / 1000
          meta_parts.append(f"Context: {context_kb:.0f}k")
        if capabilities:
          meta_parts.append(f"Capabilities: {', '.join(capabilities[:3])}")
        
        if meta_parts:
          output_lines.append(f"    {' | '.join(meta_parts)}")
        
        model_count += 1
      
      if model_count == 0:
        output_lines.append(f"\nNo models matching filter: {filter_text}")
      else:
        output_lines.append("")
        output_lines.append(f"Total: {model_count} model(s)")
      
      output_lines.append("")
      return "\n".join(output_lines)
      
    except Exception as e:
      logger.error(f"Error listing models: {e}", exc_info=True)
      return f"Error listing models: {str(e)}"

  def _model_show(self, model_name: str, registry=None, **kwargs) -> str:
    """Show detailed information about a specific model."""
    if not registry:
      return "Error: Registry not available"
    
    try:
      models = registry.get_supported_models()
      
      # Try to resolve as an alias
      resolved_name = self._resolve_model_alias(model_name, models)
      
      if resolved_name:
        if resolved_name != model_name:
          logger.info(f"Resolved alias '{model_name}' to '{resolved_name}'")
        model_def = models.get(resolved_name)
        return self._format_model_details(resolved_name, model_def)
      else:
        return f"Model not found: {model_name}\nUse :tool cli.model_list to see available models."
      
    except Exception as e:
      logger.error(f"Error getting model info: {e}", exc_info=True)
      return f"Error getting model info for '{model_name}': {str(e)}"

  def _model_current(self, active_model: str = None, active_model_source: str = None,
                     registry=None, **kwargs) -> str:
    """Show information about the current active model."""
    if not active_model:
      return "No active model selected."
    
    try:
      if registry:
        models = registry.get_supported_models()
        model_def = models.get(active_model)
        
        if model_def:
          return self._format_model_details(active_model, model_def)
      
      output = f"\nActive model: {active_model}"
      if active_model_source:
        output += f"\nSource: {active_model_source}"
      output += "\n(No additional information available)"
      return output
      
    except Exception as e:
      logger.error(f"Error getting model info: {e}", exc_info=True)
      return f"Error getting model info: {str(e)}"

  def _format_model_details(self, model_name: str, model_def) -> str:
    """Format detailed model information."""
    output_lines = []
    output_lines.append(f"\nModel: {model_name}")
    output_lines.append(DIVIDER)
    
    if getattr(model_def, 'title', None):
      output_lines.append(f"Title: {model_def.title}")
    
    if getattr(model_def, 'company', None):
      output_lines.append(f"Company: {model_def.company}")
    
    if getattr(model_def, 'description', None):
      output_lines.append(f"\nDescription:")
      output_lines.append(f"  {model_def.description}")
    
    if getattr(model_def, 'parameters', None):
      output_lines.append(f"\nParameters: {model_def.parameters}")
    
    if getattr(model_def, 'context_length', None):
      output_lines.append(f"Context Length: {model_def.context_length:,} tokens")
    
    if getattr(model_def, 'capabilities', None):
      output_lines.append(f"Capabilities: {', '.join(model_def.capabilities)}")
    
    if getattr(model_def, 'aliases', None):
      output_lines.append(f"\nAliases: {', '.join(model_def.aliases)}")
    
    if getattr(model_def, 'deployments', None):
      output_lines.append(f"\nSupported Deployments: {', '.join(model_def.deployments)}")
    
    if getattr(model_def, 'architectures', None):
      output_lines.append(f"Architectures: {', '.join(model_def.architectures)}")
    
    if getattr(model_def, 'license', None):
      output_lines.append(f"\nLicense: {model_def.license}")
    
    if getattr(model_def, 'url', None):
      output_lines.append(f"URL: {model_def.url}")
    
    if getattr(model_def, 'identifiers', None):
      output_lines.append(f"\nIdentifiers:")
      for arch, identifier in model_def.identifiers.items():
        output_lines.append(f"  {arch}: {identifier}")
    
    output_lines.append("")
    return "\n".join(output_lines)

  def _resolve_model_alias(self, model_name: str, models: Dict[str, Any]) -> Optional[str]:
    """Resolve a model name or alias to its canonical name."""
    if model_name in models:
      return model_name
    
    for canonical_name, model_def in models.items():
      aliases = getattr(model_def, 'aliases', None)
      if aliases and model_name in aliases:
        return canonical_name
    
    return None

  # ======================================================================
  # Agent Tools
  # ======================================================================
  def _agent_list(self, active_agent: str = None, default_agent: str = None,
                  registry=None, **kwargs) -> str:
    """List all available agents."""
    if not registry:
      return "Error: Registry not available"
    
    try:
      agents_info = registry.manager.get_agents()
      
      if not agents_info:
        return "No agents available."
      
      output_lines = []
      output_lines.append("\nAvailable Agents:")
      output_lines.append(DIVIDER)
      
      for agent_info in agents_info:
        agent_name = agent_info.name
        description = getattr(agent_info, 'description', 'No description available')
        
        marker = " (active)" if agent_name == active_agent else ""
        marker += " (default)" if agent_name == default_agent else ""
        
        output_lines.append(f"  • {agent_name}{marker}")
        output_lines.append(f"    {description}")
      
      output_lines.append("")
      return "\n".join(output_lines)
      
    except Exception as e:
      logger.error(f"Error listing agents: {e}", exc_info=True)
      return f"Error listing agents: {str(e)}"

  def _agent_current(self, active_agent: str = None, default_agent: str = None, **kwargs) -> str:
    """Show the current active agent."""
    current = active_agent or "None"
    default = default_agent or "None"
    
    output = f"\nCurrent active agent: {current}"
    output += f"\nDefault agent (from settings): {default}"
    return output

  # ======================================================================
  # Prompt Tools
  # ======================================================================
  def _prompt_list(self, files_directory: str, active_prompt_name: str = None,
                   default_prompt: str = None, **kwargs) -> str:
    """List all available prompts."""
    try:
      file_repo = JsonStore(files_directory)
      prompts = file_repo.list_all(artifact_type='prompts')
      
      if not prompts:
        return "No prompts found."
      
      output_lines = []
      output_lines.append("\nAvailable prompts:")
      output_lines.append(DIVIDER)
      
      for prompt_meta in prompts:
        prompt_name = prompt_meta.get('prompt_name', 'Unknown')
        
        marker = " (active)" if prompt_name == active_prompt_name else ""
        marker += " (default)" if prompt_name == default_prompt else ""
        
        output_lines.append(f"  • {prompt_name}{marker}")
      
      output_lines.append("")
      return "\n".join(output_lines)
      
    except Exception as e:
      logger.error(f"Error listing prompts: {e}", exc_info=True)
      return f"Error listing prompts: {str(e)}"

  def _prompt_print(self, files_directory: str, prompt_name: str = None,
                    active_prompt_name: str = None, **kwargs) -> str:
    """Print the content of a prompt."""
    try:
      file_repo = JsonStore(files_directory)
      
      # Determine which prompt to print
      target_name = prompt_name or active_prompt_name
      
      if not target_name:
        return "No prompt specified and no active prompt.\nUse :prompt set <name> to set an active prompt."
      
      # Find and load the prompt
      validated_name = Prompt.validate_prompt_name(target_name)
      prompts = file_repo.list_all(artifact_type='prompts')
      prompt_id = None
      
      for prompt_meta in prompts:
        if prompt_meta.get('prompt_name') == validated_name:
          prompt_id = prompt_meta.get('id')
          break
      
      if not prompt_id:
        return f"Prompt '{validated_name}' not found.\nUse :prompt list to see available prompts."
      
      prompt = file_repo.load(prompt_id)
      if not prompt:
        return f"Error loading prompt '{validated_name}'."
      
      output = f"\n{prompt.prompt_name}:"
      output += f"\n{DIVIDER}"
      output += f"\n{prompt.content}"
      output += f"\n{DIVIDER}\n"
      
      return output
      
    except Exception as e:
      logger.error(f"Error printing prompt: {e}", exc_info=True)
      return f"Error printing prompt: {str(e)}"

  # ======================================================================
  # Conversation Tools
  # ======================================================================
  def _conversation_list(self, files_directory: str, active_conversation_id: str = None, **kwargs) -> str:
    """List all saved conversations."""
    try:
      file_repo = JsonStore(files_directory)
      conversations = file_repo.list_all(artifact_type='conversations')
      
      if not conversations:
        return "No saved conversations found."
      
      output_lines = []
      output_lines.append("\nSaved conversations:")
      output_lines.append(DIVIDER)
      
      # Sort by updated_at (most recent first)
      conversations.sort(key=lambda c: c.get('updated_at', 0), reverse=True)
      
      for conv_meta in conversations:
        conv_id = conv_meta.get('id', 'Unknown')
        title = conv_meta.get('title', 'Untitled')
        updated_at = conv_meta.get('updated_at', 0)
        
        marker = " (active)" if conv_id == active_conversation_id else ""
        
        time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(updated_at)) if updated_at else "Unknown"
        
        output_lines.append(f"  • {title}{marker}")
        output_lines.append(f"    ID: {conv_id}")
        output_lines.append(f"    Updated: {time_str}")
      
      output_lines.append("")
      return "\n".join(output_lines)
      
    except Exception as e:
      logger.error(f"Error listing conversations: {e}", exc_info=True)
      return f"Error listing conversations: {str(e)}"

  def _conversation_print(self, conversation=None, **kwargs) -> str:
    """Print the entire active conversation."""
    if not conversation:
      return "No active conversation."
    
    output_lines = []
    
    # Title header
    title = getattr(conversation, 'title', 'Untitled')
    output_lines.append(f"\n{'=' * 70}")
    output_lines.append(f"{title.center(70)}")
    output_lines.append(f"{'=' * 70}\n")
    
    messages = getattr(conversation, 'messages', [])
    if not messages:
      output_lines.append("(No messages in conversation)")
    else:
      for i, msg in enumerate(messages):
        role = self._prettify_role(msg.speaker)
        output_lines.append(f"[{role}]")
        output_lines.append("-" * 70)
        
        if msg.content:
          output_lines.append(msg.content)
        else:
          output_lines.append("(empty message)")
        
        if i < len(messages) - 1:
          output_lines.append("")
    
    output_lines.append("")
    output_lines.append(f"{'=' * 70}")
    output_lines.append(f"{f'{len(messages)} message(s)'.center(70)}")
    output_lines.append(f"{'=' * 70}\n")
    
    return "\n".join(output_lines)

  def _conversation_details(self, conversation=None, **kwargs) -> str:
    """Show metadata and technical info about the active conversation."""
    if not conversation:
      return "No active conversation."
    
    output_lines = []
    output_lines.append(f"\nConversation Details:")
    output_lines.append(DIVIDER)
    output_lines.append(f"  Title: {getattr(conversation, 'title', 'Untitled')}")
    output_lines.append(f"  ID: {getattr(conversation, 'id', 'Unknown')}")
    
    messages = getattr(conversation, 'messages', [])
    output_lines.append(f"  Messages: {len(messages)}")
    
    created_at = getattr(conversation, 'created_at', None)
    updated_at = getattr(conversation, 'updated_at', None)
    
    if created_at:
      created_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at))
      output_lines.append(f"  Created: {created_str}")
    if updated_at:
      updated_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated_at))
      output_lines.append(f"  Updated: {updated_str}")
    
    prompt = getattr(conversation, 'prompt', None)
    if prompt and isinstance(prompt, dict) and prompt.get('system'):
      prompt_preview = prompt['system'][:100]
      if len(prompt['system']) > 100:
        prompt_preview += "..."
      output_lines.append(f"\n  System Prompt: {prompt_preview}")
    
    settings = getattr(conversation, 'settings', None)
    if settings:
      output_lines.append(f"\n  Settings:")
      if hasattr(settings, 'model'):
        output_lines.append(f"    Model: {settings.model or 'None'}")
      if hasattr(settings, 'temperature'):
        output_lines.append(f"    Temperature: {settings.temperature}")
      if hasattr(settings, 'max_tokens'):
        output_lines.append(f"    Max Tokens: {settings.max_tokens or 'Default'}")
    
    tool_definitions = getattr(conversation, 'tool_definitions', None)
    if tool_definitions:
      output_lines.append(f"\n  Tool Definitions: {len(tool_definitions)}")
    
    events = getattr(conversation, 'events', None)
    if events:
      output_lines.append(f"  Events (audit trail): {len(events)}")
    
    if messages:
      role_counts = {}
      for msg in messages:
        role_name = self._prettify_role(msg.speaker)
        role_counts[role_name] = role_counts.get(role_name, 0) + 1
      
      output_lines.append(f"\n  Message Breakdown:")
      for role, count in sorted(role_counts.items()):
        output_lines.append(f"    {role}: {count}")
    
    output_lines.append("")
    return "\n".join(output_lines)

  def _prettify_role(self, role) -> str:
    """Convert a MessageRole enum to a prettified string."""
    if isinstance(role, MessageRole):
      role_str = role.value
    else:
      role_str = str(role).lower()
    return role_str.capitalize()

  # ======================================================================
  # Settings Tools
  # ======================================================================
  def _settings_get(self, setting_name: str = None, settings=None, **kwargs) -> str:
    """Get the value of a setting or all settings."""
    if not settings:
      return "Error: Settings not available"
    
    try:
      if setting_name:
        current_value, default_value, help_text, category = settings.get_setting_info(setting_name)
        
        if current_value is None and not help_text:
          return f"Unknown setting: {setting_name}\nUse :help to see available settings."
        
        display_value = settings._mask_sensitive_value(setting_name, current_value)
        
        output = f"\n{setting_name}: {display_value}"
        if help_text:
          output += f"\n  ({help_text})"
        return output
      else:
        # Get all settings grouped by category
        from claia.cli.settings import SettingCategory
        
        output_lines = []
        output_lines.append("\n" + "=" * 70)
        output_lines.append("                         CURRENT SETTINGS                           ")
        output_lines.append("=" * 70)
        
        categorized = settings.get_all_settings_info()
        
        for category in SettingCategory:
          if category in categorized:
            output_lines.append(f"{category.value}:")
            output_lines.append("-" * 70)
            for var_name, display_value, help_text in categorized[category]:
              output_lines.append(f"  {var_name:30s} = {display_value}")
            output_lines.append("")
        
        output_lines.append("=" * 70)
        return "\n".join(output_lines)
        
    except Exception as e:
      logger.error(f"Error getting settings: {e}", exc_info=True)
      return f"Error getting settings: {str(e)}"

  # ======================================================================
  # System Tools
  # ======================================================================
  def _version(self, **kwargs) -> str:
    """Show CLAIA version information."""
    try:
      version = importlib_metadata.version("claia")
    except importlib_metadata.PackageNotFoundError:
      version = "dev"
    except Exception:
      version = "unknown"
    
    version_text = f"CLAIA version {version}"
    version_text += f"\nPython {sys.version.split()[0]}"
    version_text += f"\nPlatform: {sys.platform}"
    
    return version_text

  def _help(self, registry=None, command_specs=None, current_mode: str = "interactive", **kwargs) -> str:
    """Show help information."""
    output_lines = []
    output_lines.append("\n" + "=" * 70)
    output_lines.append("                             CLAIA HELP                              ")
    output_lines.append("=" * 70)
    
    # Built-in Commands
    output_lines.append("BUILT-IN COMMANDS")
    output_lines.append("-" * 70)
    
    if command_specs:
      if current_mode == 'interactive':
        output_lines.append("  Commands (prefix with ':'):")
        for aliases, _, help_desc, _, _, _ in command_specs:
          aliases_str = ', '.join(aliases)
          output_lines.append(f"    :{aliases_str:24s} - {help_desc}")
      else:
        output_lines.append("  Command Line Flags:")
        for aliases, _, help_desc, _, _, _ in command_specs:
          cli_aliases = [f"-{a}" if len(a) == 1 else f"--{a}" for a in aliases]
          aliases_str = ', '.join(cli_aliases)
          output_lines.append(f"    {aliases_str:25s} - {help_desc}")
    else:
      output_lines.append("  (Command specifications not available)")
    
    output_lines.append("")
    
    # Available Tools/Modules
    output_lines.append("AVAILABLE TOOLS & MODULES")
    output_lines.append("-" * 70)
    
    if registry:
      catalog = registry.get_commands_catalog()
      if catalog:
        total_tools = 0
        for mod_name, mod in catalog.items():
          info = mod.get('module_info')
          title = getattr(info, 'title', None) if info else None
          desc = getattr(info, 'description', None) if info else None
          
          line = f"  [{mod_name}]"
          if title:
            line += f" {title}"
          output_lines.append(line)
          if desc:
            output_lines.append(f"    {desc}")
          
          tools = mod.get('list_of_tools', [])
          if tools:
            for tool in tools:
              tool_name = tool.get('tool_name')
              tool_desc = tool.get('tool_description', '')
              output_lines.append(f"    • {mod_name}.{tool_name:20s} - {tool_desc}")
              total_tools += 1
          else:
            output_lines.append(f"    (no tools available)")
          output_lines.append("")
        
        output_lines.append(f"  Total: {len(catalog)} module(s), {total_tools} tool(s)")
      else:
        output_lines.append("  No modules loaded")
    else:
      output_lines.append("  (Registry not available)")
    
    output_lines.append("")
    output_lines.append("=" * 70)
    
    return "\n".join(output_lines)

