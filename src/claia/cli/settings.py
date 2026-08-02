"""
This module manages the configuration settings for the CLAIA application.

It maintains a unified ``ParamSpec`` registry for all configurable
settings — application-level (``claia.cli.params.APP_PARAMS``) plus any
plugin-declared specs pulled in from the registry. Values are loaded
from CLI args, environment variables, .env files, and ``settings.json``,
with deterministic precedence.

Single source of truth: every setting is described by a ``ParamSpec``;
there is no parallel tuple list to keep in sync.
"""

# External dependencies
import os
import argparse
import json
import logging
from collections import defaultdict, OrderedDict
from typing import Dict, Any, List, Tuple, Optional
from dotenv import load_dotenv

# Internal dependencies
from ..core.enums.logging import LogLevel, LogFormat
from ..core.plugins.base import ParamScope, ParamSpec, SettingCategory
from .params import APP_PARAMS
from ..framework.manager import Manager
from ..framework.registry import Registry


########################################################################
#                               CONSTANTS                              #
########################################################################
DEFAULT_LOG_LEVEL  = LogLevel.WARNING
DEFAULT_LOG_FORMAT = LogFormat.STANDARD
DEFAULT_ENV_FILE = ".env"
DEFAULT_SETTINGS_FILE = "settings.json"
ENV_PREFIX = "CLAIA_"

# Sentinel "unset" values per type. RUNTIME params use these to indicate
# "let the plugin's spec default apply" rather than "force this value".
_RUNTIME_SENTINELS = {
  str: "",
  int: None,
  float: None,
  bool: None,
}


logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class Settings:
  """
  Stores and manages configuration settings for the CLAIA application.

  Internally backed by ``self.config_specs`` (an ordered mapping of
  ``name -> ParamSpec``). All app-level and plugin-declared settings
  share this single registry; RUNTIME-scoped specs are tracked
  separately so they can be selectively threaded into per-call kwargs.
  """

  def __init__(self, registry: 'Registry' = None):
    """
    Initialize configuration from environment variables and command line arguments.

    Args:
      registry: Optional Registry instance for discovering extension settings.
                If provided, every plugin-declared ``ParamSpec`` is
                absorbed as a dynamic setting.
    """
    self.loaded_local_models: Dict[str, Any] = {}

    self.prompt_store = []
    self.extra_args = []

    self.active_model = None
    self.active_model_source = None
    self.active_agent = None
    self.active_prompt = None
    self.active_conversation = None

    self.root_logger = None

    # Track which settings came from CLI (to avoid saving them to file)
    self._cli_sourced_settings: set = set()

    # Unified spec registry: name -> ParamSpec. Insertion order matters
    # (preserves CONFIG_VARS-equivalent ordering for help output).
    self.config_specs: "OrderedDict[str, ParamSpec]" = OrderedDict()
    for spec in APP_PARAMS:
      self.config_specs[spec.name] = spec

    self._extension_settings: List[str] = []

    # Track secret ParamSpecs by name so sensitive values get masked in
    # display output regardless of whether their name contains
    # 'token'/'password'.
    self._secret_settings: set = {
      spec.name for spec in self.config_specs.values() if spec.secret
    }

    # Extend with extension settings if registry is provided
    if registry is not None:
      self._extend_with_extensions(registry)

    # Load configuration
    self._load_config()
    self.validate()

    # Save settings to file after loading (creates file if doesn't exist, updates if values changed)
    self._save_settings_to_file()

  # ----------------------------------------------------------------
  # Spec helpers
  # ----------------------------------------------------------------
  def _is_unset(self, spec: ParamSpec, value: Any) -> bool:
    """True if ``value`` matches the sentinel-unset for ``spec``'s type."""
    sentinel = _RUNTIME_SENTINELS.get(spec.type, None)
    return value is None or value == sentinel

  def _extend_with_extensions(self, registry: 'Registry') -> None:
    """
    Absorb plugin-declared ``ParamSpec`` objects into ``config_specs``.

    Both ``INIT``- and ``RUNTIME``-scoped specs are absorbed:
      - INIT specs configure the plugin at construction time (API
        tokens, endpoints, ...). They flow through ``get_user_kwargs``
        on every call.
      - RUNTIME specs are per-call generation knobs (temperature,
        max_tokens, ...). They flow through ``get_runtime_kwargs`` and
        are merged with per-call overrides at dispatch time.

    First declaration wins: if a plugin tries to redeclare an already-known
    setting (either app-level or another plugin's), it is skipped.
    """
    specs = registry.get_extension_params(scope=None)  # both INIT and RUNTIME

    for spec in specs:
      if spec.name in self.config_specs:
        continue
      self.config_specs[spec.name] = spec
      self._extension_settings.append(spec.name)
      if spec.secret:
        self._secret_settings.add(spec.name)

  @staticmethod
  def _generate_help_text(arg_name: str) -> str:
    """Fallback help text: snake_case -> Title Case."""
    return arg_name.replace('_', ' ').title()

  def get_extension_settings(self) -> List[str]:
    """Get the list of setting names that were added from extensions."""
    return list(self._extension_settings)

  def _spec_default(self, spec: ParamSpec) -> Any:
    """
    Return the value to seed a setting with at boot.

    For RUNTIME specs we deliberately seed the sentinel-unset value (not
    the plugin's true default) so that ``get_runtime_kwargs`` can
    distinguish "user explicitly set this" from "unset, let the plugin
    apply its own default". For INIT specs we seed the spec's actual
    default.
    """
    if spec.scope == ParamScope.RUNTIME:
      return _RUNTIME_SENTINELS.get(spec.type, None)
    if spec.default is not None:
      return spec.default
    return "" if spec.type is str else spec.default

  # ----------------------------------------------------------------
  # Config loading
  # ----------------------------------------------------------------
  def _load_config(self):
    """
    Load configuration from command line arguments, .env file, and environment variables.

    Priority: CLI args > .env file > Environment variables > settings.json > spec defaults
    """
    # Disable argparse's automatic -h/--help so our custom help handler can take over
    # Disable allow_abbrev to prevent --model from matching --models-directory etc.
    parser = argparse.ArgumentParser(description='CLAIA Settings', add_help=False, allow_abbrev=False)

    for spec in self.config_specs.values():
      if not spec.externally_settable:
        continue

      cli_name = f"--{spec.name.replace('_', '-')}"
      help_text = spec.description or self._generate_help_text(spec.name)
      if spec.choices:
        help_text = f"{help_text} (choices: {', '.join(str(c) for c in spec.choices)})"

      if spec.type is bool:
        parser.add_argument(
          cli_name,
          type=lambda x: x.lower() == 'true',
          default=None,
          help=help_text)
      elif spec.type is int:
        parser.add_argument(cli_name, type=int, default=None, help=help_text)
      elif spec.type is float:
        parser.add_argument(cli_name, type=float, default=None, help=help_text)
      else:
        parser.add_argument(cli_name, default=None, help=help_text)

    # Parse known args, and store unknown args for later command processing
    args, unknown = parser.parse_known_args()
    self.extra_args = unknown

    # Track which settings were explicitly provided via CLI
    for spec in self.config_specs.values():
      if not spec.externally_settable:
        continue
      cli_value = getattr(args, spec.name.lower(), None)
      if cli_value is not None:
        self._cli_sourced_settings.add(spec.name)

    # Load .env file if it exists (get env_file from args or use default)
    env_spec = self.config_specs.get("env_file")
    env_file = self._get_config_value(env_spec, args, {}) if env_spec else DEFAULT_ENV_FILE
    if not env_file:
      env_file = DEFAULT_ENV_FILE
    if os.path.exists(env_file):
      load_dotenv(env_file, override=True)

    # Load settings from settings.json file first (lowest priority after defaults)
    # Need to get files_directory first to know where to look for settings.json
    fd_spec = self.config_specs.get("files_directory")
    files_dir = self._get_config_value(fd_spec, args, {}) if fd_spec else "storage"
    if not files_dir:
      files_dir = "storage"
    json_settings = self._load_settings_from_file(files_dir)

    # Resolve every spec to its final value
    for spec in self.config_specs.values():
      value = self._get_config_value(spec, args, json_settings)
      setattr(self, spec.name, value)


  def _get_config_value(self, spec: ParamSpec, args: argparse.Namespace, json_settings: Dict[str, Any]) -> Any:
    """
    Resolve a single spec's value across all sources.

    Priority: CLI args > .env file > Environment variables > settings.json > Defaults
    """
    seeded_default = self._spec_default(spec)

    if not spec.externally_settable:
      return seeded_default

    env_name = spec.name.upper()
    prefixed_env_name = f"{ENV_PREFIX}{spec.name.upper()}"
    cli_name = spec.name.lower()

    value = getattr(args, cli_name, None)

    if value is None:
      value = os.getenv(prefixed_env_name)
    if value is None:
      value = os.getenv(env_name)
    if value is None and spec.name in json_settings:
      value = json_settings[spec.name]

    if value and isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
      value = value[1:-1]

    if value is None or value == "":
      return seeded_default

    coerced = Manager.coerce_value(value, spec.type or str)
    if coerced is Manager._COERCE_FAIL:
      display = Manager._mask_for_log(value, spec)
      logger.warning(
        f"Could not coerce setting {spec.name}={display!r} to {spec.type.__name__}; "
        f"falling back to default {seeded_default!r}"
      )
      return seeded_default

    if spec.choices and coerced not in spec.choices:
      display = Manager._mask_for_log(coerced, spec)
      logger.warning(
        f"Setting {spec.name}={display!r} not in allowed choices {spec.choices}; "
        f"falling back to default {seeded_default!r}"
      )
      return seeded_default

    return coerced


  def validate(self) -> bool:
    """
    Validate the configuration settings.

    Returns:
      bool: Always returns True as API token validation is handled elsewhere.
    """
    try:
      LogLevel.from_string(self.log_level)
    except ValueError:
      if self.log_level:
        print(f"Invalid log level in environment variable. Using default: {DEFAULT_LOG_LEVEL.name}")
      self.log_level = DEFAULT_LOG_LEVEL.name

    try:
      LogFormat.from_string(self.log_format)
    except ValueError:
      if self.log_format:
        print(f"Invalid log format in environment variable. Using default: {DEFAULT_LOG_FORMAT.name}")
      self.log_format = DEFAULT_LOG_FORMAT.name

    return True

  # ----------------------------------------------------------------
  # Kwargs surfaces
  # ----------------------------------------------------------------
  def get_user_kwargs(self) -> Dict[str, Any]:
    """
    Return all user-supplied configuration values as kwargs.

    Includes:
      - All ``INIT`` specs (with their resolved values, including
        defaults) so the registry can construct plugins correctly.
      - All ``RUNTIME`` specs that the user has explicitly overridden
        (i.e., values that differ from the unset sentinel). RUNTIME
        specs left at the sentinel are omitted so that the model's
        own spec defaults stay in effect.
    """
    kwargs: Dict[str, Any] = {}
    for spec in self.config_specs.values():
      if not spec.externally_settable:
        continue
      value = getattr(self, spec.name, self._spec_default(spec))
      if spec.scope == ParamScope.RUNTIME and self._is_unset(spec, value):
        continue
      kwargs[spec.name] = value
    return kwargs

  def get_runtime_kwargs(self) -> Dict[str, Any]:
    """
    Return only the explicitly-set RUNTIME specs.

    Used by callers that want to merge user-set generation knobs into a
    per-call ``registry.run`` invocation without dragging the full INIT
    surface along.
    """
    kwargs: Dict[str, Any] = {}
    for spec in self.config_specs.values():
      if spec.scope != ParamScope.RUNTIME or not spec.externally_settable:
        continue
      value = getattr(self, spec.name, self._spec_default(spec))
      if self._is_unset(spec, value):
        continue
      kwargs[spec.name] = value
    return kwargs


  # ----------------------------------------------------------------
  # File persistence
  # ----------------------------------------------------------------
  def _load_settings_from_file(self, files_directory: str) -> Dict[str, Any]:
    """Load settings from settings.json file in the files directory."""
    settings_path = os.path.join(files_directory, DEFAULT_SETTINGS_FILE)

    if not os.path.exists(settings_path):
      return {}

    try:
      with open(settings_path, 'r') as f:
        return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
      print(f"Warning: Could not load settings from {settings_path}: {e}")
      return {}


  def _save_settings_to_file(self) -> None:
    """
    Save current settings to settings.json file in the files directory.

    Only saves externally settable values. Excludes settings that were
    provided via CLI arguments (those are ephemeral). RUNTIME specs at
    their unset sentinel are also skipped so a clear/reset removes the
    entry from disk entirely.
    """
    settings_path = os.path.join(self.files_directory, DEFAULT_SETTINGS_FILE)

    os.makedirs(self.files_directory, exist_ok=True)

    existing_settings = {}
    if os.path.exists(settings_path):
      try:
        with open(settings_path, 'r') as f:
          existing_settings = json.load(f)
      except (json.JSONDecodeError, IOError):
        pass  # If we can't read it, we'll overwrite it

    current_settings: Dict[str, Any] = {}
    for spec in self.config_specs.values():
      if not spec.externally_settable:
        continue
      value = getattr(self, spec.name, self._spec_default(spec))

      if spec.name in self._cli_sourced_settings:
        if spec.name in existing_settings:
          current_settings[spec.name] = existing_settings[spec.name]
        continue

      if spec.scope == ParamScope.RUNTIME and self._is_unset(spec, value):
        continue

      current_settings[spec.name] = value

    if current_settings != existing_settings:
      try:
        with open(settings_path, 'w') as f:
          json.dump(current_settings, f, indent=2)
      except IOError as e:
        print(f"Warning: Could not save settings to {settings_path}: {e}")


  # ----------------------------------------------------------------
  # Public introspection
  # ----------------------------------------------------------------
  def get_unset_api_keys(self) -> List[Tuple[str, str]]:
    """Return (name, help_text) for every API-category setting that is empty."""
    unset_keys = []
    for spec in self.config_specs.values():
      if spec.category != SettingCategory.API or not spec.externally_settable:
        continue
      value = getattr(self, spec.name, self._spec_default(spec))
      help_text = spec.description or self._generate_help_text(spec.name)
      if not value or value == self._spec_default(spec):
        unset_keys.append((spec.name, help_text))
    return unset_keys


  def get_setting_info(self, setting_name: str) -> Tuple[Any, Any, str, SettingCategory]:
    """
    Get information about a specific setting.

    Returns:
      (current_value, default_value, help_text, category) — all None/empty
      if the setting is unknown or not externally settable.
    """
    setting_name = setting_name.lower().replace('-', '_')
    spec = self.config_specs.get(setting_name)
    if spec is None or not spec.externally_settable:
      return (None, None, "", None)
    current_value = getattr(self, spec.name, self._spec_default(spec))
    help_text = spec.description or self._generate_help_text(spec.name)
    category = spec.category if spec.category is not None else SettingCategory.MISC
    return (current_value, self._spec_default(spec), help_text, category)


  def get_all_settings_info(self) -> Dict[SettingCategory, List[Tuple[str, Any, str]]]:
    """
    Get all externally settable settings grouped by category.

    Returns:
      Dictionary mapping category to list of (name, display_value, help_text) tuples.
      RUNTIME specs are decorated with "(default)" when at the sentinel.
    """
    categorized: Dict[SettingCategory, List[Tuple[str, Any, str]]] = defaultdict(list)
    for spec in self.config_specs.values():
      if not spec.externally_settable:
        continue
      value = getattr(self, spec.name, self._spec_default(spec))
      help_text = spec.description or self._generate_help_text(spec.name)
      category = spec.category if spec.category is not None else SettingCategory.MISC

      if spec.scope == ParamScope.RUNTIME and self._is_unset(spec, value):
        display_value = "(plugin default)"
      else:
        display_value = self._mask_sensitive_value(spec.name, value)

      categorized[category].append((spec.name, display_value, help_text))
    return categorized


  def is_valid_setting(self, setting_name: str) -> bool:
    """Check whether ``setting_name`` is a known, externally settable spec."""
    setting_name = setting_name.lower().replace('-', '_')
    spec = self.config_specs.get(setting_name)
    return spec is not None and spec.externally_settable


  def update_setting(self, setting_name: str, value: Any) -> Tuple[bool, str, Any]:
    """
    Update a setting with type coercion and validation.

    Returns:
      (success, message, old_value). On failure the old value is preserved.
    """
    setting_name = setting_name.lower().replace('-', '_')
    spec = self.config_specs.get(setting_name)
    if spec is None or not spec.externally_settable:
      return (False, f"Unknown setting: {setting_name}", None)

    coerced = Manager.coerce_value(value, spec.type or str)
    if coerced is Manager._COERCE_FAIL:
      display = Manager._mask_for_log(value, spec)
      return (False, f"Invalid value for {setting_name}: {display!r}", None)

    if spec.choices and coerced not in spec.choices:
      return (
        False,
        f"Invalid value for {setting_name}: {coerced!r}. "
        f"Allowed: {spec.choices}",
        None,
      )

    old_value = getattr(self, setting_name, None)
    setattr(self, setting_name, coerced)

    # Remove from CLI sourced settings if present (so it will be saved to file)
    if setting_name in self._cli_sourced_settings:
      self._cli_sourced_settings.remove(setting_name)

    try:
      self._save_settings_to_file()
      return (True, f"Setting '{setting_name}' updated successfully", old_value)
    except Exception as e:
      setattr(self, setting_name, old_value)
      return (False, f"Failed to save setting: {str(e)}", old_value)


  def reset_setting(self, setting_name: str) -> Tuple[bool, str, Any]:
    """
    Clear a setting back to its default (or, for RUNTIME specs, back to
    "use plugin default").

    Returns:
      (success, message, old_value).
    """
    setting_name = setting_name.lower().replace('-', '_')
    spec = self.config_specs.get(setting_name)
    if spec is None or not spec.externally_settable:
      return (False, f"Unknown setting: {setting_name}", None)

    old_value = getattr(self, setting_name, None)
    setattr(self, setting_name, self._spec_default(spec))

    if setting_name in self._cli_sourced_settings:
      self._cli_sourced_settings.remove(setting_name)

    try:
      self._save_settings_to_file()
      return (True, f"Setting '{setting_name}' reset to default", old_value)
    except Exception as e:
      setattr(self, setting_name, old_value)
      return (False, f"Failed to save setting: {str(e)}", old_value)


  def reset_runtime_settings(self) -> List[str]:
    """
    Reset every RUNTIME spec back to its unset sentinel. Returns the list
    of setting names that were actually changed.
    """
    changed: List[str] = []
    for spec in self.config_specs.values():
      if spec.scope != ParamScope.RUNTIME or not spec.externally_settable:
        continue
      current = getattr(self, spec.name, self._spec_default(spec))
      if self._is_unset(spec, current):
        continue
      setattr(self, spec.name, self._spec_default(spec))
      if spec.name in self._cli_sourced_settings:
        self._cli_sourced_settings.remove(spec.name)
      changed.append(spec.name)

    if changed:
      try:
        self._save_settings_to_file()
      except Exception as e:
        logger.warning(f"Failed to persist runtime reset: {e}")
    return changed


  def _mask_sensitive_value(self, var_name: str, value: Any) -> Any:
    """Mask sensitive values (tokens, passwords) for display."""
    is_secret = (
      var_name in self._secret_settings
      or 'token' in var_name.lower()
      or 'password' in var_name.lower()
    )
    if is_secret:
      if value and value != "":
        return "***" + str(value)[-4:] if len(str(value)) > 4 else "***"
    return value
