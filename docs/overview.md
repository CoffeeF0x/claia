# CLAIA Developer Guide (src/)

This guide explains the package layout, how to add a model, create an agent, add tool commands, and use the CLI.

## Package Overview

- `claia/` — core package
  - `agents/` — agent implementations and plugins
  - `cli/` — CLI entrypoint, settings, defaults, logger
  - `deployments/` — runtime backends (API, local, remote, dummy)
  - `hooks/` — plugin hook contracts (types and info objects)
  - `lib/` — shared runtime library
    - `base.py` — base agent utilities
    - `files/` — file, prompt, and conversation types
    - `model/` — model layer (API, transformers, dummy, base classes)
    - `process.py`, `queue.py`, `results.py` — orchestration utilities
  - `architectures/` — architecture plugins that map to model classes
  - `definitions/` — definitions that name and describe models
  - `solvers/` — select model per process
  - `tools/` — concrete tool command modules
  - `tool_patterns/` — patterns that define tool prompts/format
  - `tool_protocols/` — protocols that execute commands from a catalog

Plugin registration uses Python entry points declared in `pyproject.toml` under:
- `claia.architectures`, `claia.definitions`, `claia.deployments`, `claia.solvers`, `claia.agents`
- `claia.tool_modules`, `claia.tool_patterns`, `claia.tool_protocols`

See `pyproject.toml` for current built-in registrations.

## Add a Model

You add models by providing:
1) A model class in `claia/lib/model/...`
2) An architecture plugin in `claia/architectures/`
3) (Optional) a definitions plugin in `claia/definitions/`
4) An entry point in `pyproject.toml`

Step 1: Implement or reuse a model class
- Place API-backed clients under `claia/lib/model/api/` (e.g., `openai.py`, `anthropic.py`).
- Place local/transformer models under `claia/lib/model/transformers/`.
- Base interfaces live in `claia/lib/model/base/`.

Step 2: Create an architecture plugin
Create `claia/architectures/my_provider.py` that returns the model class and declares its `ParamSpec`s for safe kwarg filtering.

```python
import pluggy
from typing import Type
from claia.lib.model.api import OpenAIModel  # or your own model class
from claia.core.plugins.base import ArchitectureInfo, ParamScope, ParamSpec, SettingCategory

hookimpl = pluggy.HookimplMarker("claia_architectures")

class MyProviderPlugin:
  @hookimpl
  def get_architecture_info(self) -> ArchitectureInfo:
    return ArchitectureInfo(
      name="my_provider",
      title="My Provider API",
      description="My provider models",
      params=[
        ParamSpec(
          name="my_provider_api_token",
          type=str,
          scope=ParamScope.INIT,
          required=True,
          secret=True,
          category=SettingCategory.API,
          description="My Provider API Token",
        ),
      ],
    )

  @hookimpl
  def get_model_class(self) -> Type:
    return OpenAIModel  # or your custom class
```

Step 3 (optional): Add model definitions
If you want human-friendly IDs and metadata, provide `claia/definitions/my_provider.py` with a definitions plugin that enumerates supported models.

Step 4: Register entry points in `pyproject.toml`

```toml
[project.entry-points."claia.architectures"]
my_provider = "claia.architectures.my_provider:MyProviderPlugin"

# Optional: definitions
[project.entry-points."claia.definitions"]
my_provider = "claia.definitions.my_provider:MyProviderDefinitionsPlugin"
```

Credentials and config are provided via CLI flags or env vars (see CLI section). The registry forwards only the kwargs that match a `ParamSpec` declared by the plugin.

## Create an Agent

Agents orchestrate a `Process` using the model registry. Implement an agent class and expose it via an agent plugin.

```python
import pluggy
from claia.lib import BaseAgent

hookimpl = pluggy.HookimplMarker("claia_agents")

class MyAgent(BaseAgent):
  @classmethod
  def process_request(cls, process, registry=None, **kwargs):
    model_id = process.parameters["model_id"]
    result = registry.run(model_id, process.conversation, **kwargs)
    if result.is_error():
      process.mark_failed(result.get_message())
    else:
      process.mark_completed(result.get_data())
    return process

class MyAgentPlugin:
  @hookimpl
  def get_agent_class(self, agent_name: str):
    return MyAgent if agent_name == "my_agent" else None

  @hookimpl
  def get_agent_info(self):
    from claia.hooks import AgentInfo
    return AgentInfo(name="my_agent", description="Custom agent")
```

Register it in `pyproject.toml`:

```toml
[project.entry-points."claia.agents"]
my_agent = "claia.agents.my_agent:MyAgentPlugin"
```

Pick it at runtime with `--default-agent my_agent` or interactively in the CLI.

## Add Tool Commands

Tool commands are provided by command modules. The registry validates/serializes arguments and passes prepared kwargs to the protocol. Protocols execute commands from a commands catalog (not the full manager).

Implement a module in `claia/tools/my_module.py`:

```python
import pluggy
from claia.hooks.tool import ToolModuleInfo, ToolDefinition, ArgumentDefinition

hookimpl = pluggy.HookimplMarker("claia_tool_modules")

class MyModulePlugin:
  @hookimpl
  def get_module_info(self) -> ToolModuleInfo:
    return ToolModuleInfo(name="my", title="My Tools", description="Demo tools")

  @hookimpl
  def get_module_tools(self):
    return {
      "echo": ToolDefinition(
        name="echo",
        description="Echo a message",
        callable=lambda message, **kw: str(message),
        arguments={
          "message": ArgumentDefinition(name="message", data_type="str", required=True, description="Message")
        }
      )
    }
```

Register it in `pyproject.toml`:

```toml
[project.entry-points."claia.tool_modules"]
my = "claia.tools.my_module:MyModulePlugin"
```

Notes:
- Protocols (e.g., `tool_protocols.simple`) receive a commands catalog and invoke callables. See `claia/tool_protocols/simple.py`.
- Patterns (e.g., `tool_patterns/default.py`) provide prompts for tool calling.

## Use the CLI

Run the CLI:

```bash
python -m claia
# or, after install
claia
```

Configuration sources (priority: CLI flags > .env > env vars > defaults):
- CLI flags are auto-generated from `claia/cli/settings.py` `CONFIG_VARS` (e.g., `--openai-api-token`, `--default-agent`).
- `.env` supports `CLAIA_`-prefixed variables or unprefixed (e.g., `CLAIA_OPENAI_API_TOKEN=...`).

One-shot command execution (non-interactive):

```bash
# Call a tool command directly
claia my.echo message="Hello"

# Run any registered command: <module>.<command> key=value [key=value ...]
claia sample.add a=1 b=2
```

Interactive commands:
- Enter `:` to run commands inside the REPL
- `:` (alone) shows help information
- `:tool` lists available modules
- `:tool sample` lists commands in the `sample` module
- `:sample.echo message=Hello` or `:tool sample.echo message=Hello` runs a command

Model inference (interactive):
- Type a prompt (no leading `:`). The default agent (e.g., `bob`) creates a `Process` and calls the selected model via the registry.
- Change defaults with flags like `--default-model`, `--default-agent`, etc.

Workers and tools:
- The CLI initializes a `Registry` with background workers and default tool pattern/protocol so tool calls in model outputs can be detected and executed.

## Testing

Run tests from the project root:

```bash
pytest -q
