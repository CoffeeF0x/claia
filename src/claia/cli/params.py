"""
App/CLI-level parameter declarations for CLAIA.

This is the canonical source of truth for application-wide settings that
are not owned by any specific plugin (architecture/deployment/agent/etc).
Plugin-owned parameters are declared on the plugin itself via
``ExtensionInfo.params`` and pulled in dynamically by
``Settings._extend_with_extensions``.

All app-level params are ``INIT``-scoped: they configure how the
application behaves at startup (logging, directories, defaults, etc.) and
are not per-call generation knobs.

To add a new app-level setting, append a ``ParamSpec`` to ``APP_PARAMS``
below. Settings will pick it up automatically — there is no separate
``CONFIG_VARS`` to keep in sync.
"""

# External dependencies
from typing import List

# Internal dependencies
from claia.core.plugins.base import ParamScope, ParamSpec, SettingCategory


APP_PARAMS: List[ParamSpec] = [
  # ====================================================================
  # API Tokens (those NOT owned by a built-in plugin)
  # Plugin-owned API tokens (openai, anthropic, huggingface) are declared
  # on their respective architectures and merged in at startup.
  # ====================================================================
  ParamSpec(
    name="local_llm_api_token",
    type=str, scope=ParamScope.INIT, default="",
    secret=True, category=SettingCategory.API,
    description="LocalLLM API Token",
  ),
  ParamSpec(
    name="runpod_api_token",
    type=str, scope=ParamScope.INIT, default="",
    secret=True, category=SettingCategory.API,
    description="RunPod API Token",
  ),
  ParamSpec(
    name="massed_compute_api_token",
    type=str, scope=ParamScope.INIT, default="",
    secret=True, category=SettingCategory.API,
    description="Massed Compute API Token",
  ),
  ParamSpec(
    name="openrouter_api_token",
    type=str, scope=ParamScope.INIT, default="",
    secret=True, category=SettingCategory.API,
    description="OpenRouter API Token",
  ),
  ParamSpec(
    name="cloudflare_api_token",
    type=str, scope=ParamScope.INIT, default="",
    secret=True, category=SettingCategory.API,
    description="Cloudflare API Token",
  ),

  # ====================================================================
  # URLs and Endpoints
  # ====================================================================
  ParamSpec(
    name="local_llm_base_url",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.ENDPOINT,
    description="LocalLLM Base URL",
  ),

  # ====================================================================
  # Directories
  # ====================================================================
  ParamSpec(
    name="files_directory",
    type=str, scope=ParamScope.INIT, default="storage",
    category=SettingCategory.DIRECTORY,
    description="Directory for generated, converted, or imported files",
  ),
  ParamSpec(
    name="models_directory",
    type=str, scope=ParamScope.INIT, default="models",
    category=SettingCategory.DIRECTORY,
    description="Directory for model files",
  ),

  # ====================================================================
  # Model defaults
  # ====================================================================
  ParamSpec(
    name="default_model",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.MODEL,
    description="Default model name",
  ),
  ParamSpec(
    name="default_model_source",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.MODEL,
    description="Default model source",
  ),

  # ====================================================================
  # Prompt defaults
  # ====================================================================
  ParamSpec(
    name="default_prompt",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.PROMPT,
    description="Default prompt name to use",
  ),

  # ====================================================================
  # Agent defaults
  # ====================================================================
  ParamSpec(
    name="default_agent",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.AGENT,
    description="Default agent type",
  ),

  # ====================================================================
  # VLLM Settings
  # ====================================================================
  ParamSpec(
    name="vllm_zone",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.VLLM,
    description="VLLM Zone",
  ),
  ParamSpec(
    name="vllm_email",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.VLLM,
    description="VLLM Email",
  ),
  ParamSpec(
    name="vllm_subdomain",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.VLLM,
    description="VLLM Subdomain",
  ),
  ParamSpec(
    name="vllm_eab_kid",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.VLLM,
    description="VLLM EAB Kid",
  ),
  ParamSpec(
    name="vllm_eab_hmac_encoded",
    type=str, scope=ParamScope.INIT, default="",
    secret=True, category=SettingCategory.VLLM,
    description="VLLM EAB HMAC Encoded",
  ),

  # ====================================================================
  # Application Settings
  # ====================================================================
  ParamSpec(
    name="log_level",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.APPLICATION,
    description="Logging level",
  ),
  ParamSpec(
    name="log_format",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.APPLICATION,
    description="Logging format (simple, standard, detailed)",
  ),
  ParamSpec(
    name="log_file",
    type=str, scope=ParamScope.INIT, default="claia.log",
    category=SettingCategory.APPLICATION,
    description="Log file path (empty for console only)",
  ),
  ParamSpec(
    name="env_file",
    type=str, scope=ParamScope.INIT, default="",
    category=SettingCategory.APPLICATION,
    description="Path to .env file for configuration",
  ),
  ParamSpec(
    name="suppress_setup_notice",
    type=bool, scope=ParamScope.INIT, default=False,
    category=SettingCategory.APPLICATION,
    description="Suppress API key setup notice on startup",
  ),
]
