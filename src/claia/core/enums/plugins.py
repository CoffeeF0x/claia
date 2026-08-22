from enum import Enum


class SettingCategory(Enum):
  """Categories for grouping parameters in CLI / settings UIs."""
  API = "API Credentials"
  ENDPOINT = "Endpoints & URLs"
  DIRECTORY = "Directories"
  MODEL = "Model Settings"
  PROMPT = "Prompt Settings"
  AGENT = "Agent Settings"
  VLLM = "VLLM Settings"
  APPLICATION = "Application Settings"
  INTEGRATION = "External Integrations"
  EXTENSION = "Extension Settings"
  GENERATION = "Generation Parameters"
  MISC = "Miscellaneous"


class ParamScope(Enum):
  """When a parameter is consumed relative to the plugin lifecycle."""
  INIT = "init"        # Passed at plugin construction (credentials, config)
  RUNTIME = "runtime"  # Passed per call (generation params, per-request overrides)
