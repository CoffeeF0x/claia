from enum import Enum


class ParamCategory(Enum):
  """Optional grouping hint on a ``ParamSpec``.

  Hosts that present parameters (the CLI settings UI, help, setup)
  use this to cluster related specs. Core and the framework do not
  interpret it.
  """
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
