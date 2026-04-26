# CLAIA Developer Overview

CLAIA is split into three layers under the `claia.*` namespace: `core` for pure library code, `framework` for orchestration, and `cli` for the command-line app. Start with `claia.framework.Registry` when building an app, and drop into `claia.core` when you are adding models, tools, or data types.

## Package Overview

- `claia.core` — data models, result types, plugin metadata/contracts, model classes, architectures, deployments, solvers, definitions, and tools.
- `claia.framework` — pluggy discovery, registrars, hookspecs, `Registry`, `Process`, `ProcessQueue`, worker lifecycle, and agents.
- `claia.cli` — argument parsing, settings, interactive commands, rendering, CLI tool module, and JSON file storage.

Plugin registration uses Python entry points declared in `pyproject.toml`:

- `claia.architectures`, `claia.definitions`, `claia.deployments`, `claia.solvers`, `claia.agents`
- `claia.tool_modules`, `claia.tool_patterns`, `claia.tool_protocols`

## Use CLAIA As A Library

```python
from claia.framework import Registry, Conversation
from claia.core.enums.conversation import MessageRole

registry = Registry()
registry.load_plugins(openai_api_token="sk-...")

conversation = Conversation(title="Example")
conversation.add_message(MessageRole.USER, "Explain registries in one sentence.")

result = registry.run("gpt-4", conversation, temperature=0.3)
print(result.get_data() if result.is_success() else result.get_message())
```

Use `Registry.query(...)` for a one-shot prompt helper and `Registry.run_command(...)` for direct tool invocation. Use `start_workers(...)`, `add_process(...)`, and `stop_workers(...)` when you need queued agent processing.

## Add A Model Provider

Adding a provider usually means adding four pieces:

1. A model class under `claia.core.models`.
2. An architecture plugin under `claia.core.architectures`.
3. Optional model definitions under `claia.core.definitions`.
4. Entry points in `pyproject.toml`.

```python
from typing import Type

from claia.core.architectures.base import BaseArchitecture
from claia.core.models.api.openai import OpenAIModel
from claia.core.plugins.base import ArchitectureInfo, ParamScope, ParamSpec, SettingCategory


class MyProviderPlugin(BaseArchitecture):
    info = ArchitectureInfo(
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
                description="My Provider API token.",
            ),
        ],
    )

    def get_architecture_info(self) -> ArchitectureInfo:
        return self.info

    def get_model_class(self) -> Type:
        return OpenAIModel
```

Register it:

```toml
[project.entry-points."claia.architectures"]
my_provider = "claia.core.architectures.my_provider:MyProviderPlugin"

[project.entry-points."claia.definitions"]
my_provider = "claia.core.definitions.my_provider:MyProviderDefinitionsPlugin"
```

The framework filters constructor and runtime kwargs through each plugin's `ParamSpec` declarations. `ParamScope.INIT` values are used during plugin construction; `ParamScope.RUNTIME` values are resolved per request.

## Create An Agent

Agents turn a `Process` into work. They live in `claia.framework.agents`, receive the active registry, and usually call `registry.run(...)` or `registry.query(...)`.

```python
from claia.framework import BaseAgent


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
```

Expose the agent with a plugin registered under `claia.agents`. See `claia.framework.agents.simple` for the built-in implementation.

## Add Tool Commands

Tools are split into modules, patterns, and protocols:

- Tool modules provide callable commands.
- Tool patterns detect tool calls in generated text.
- Tool protocols execute calls against the command catalog.

```python
from claia.core.plugins.base import ArgumentDefinition, ToolDefinition, ToolModuleInfo
from claia.core.tools.modules.base import BaseToolModule


class MyModulePlugin(BaseToolModule):
    info = ToolModuleInfo(name="my", title="My Tools", description="Demo tools")

    def get_module_tools(self):
        return {
            "echo": ToolDefinition(
                name="echo",
                description="Echo a message.",
                callable=lambda message, **kwargs: str(message),
                arguments={
                    "message": ArgumentDefinition(
                        name="message",
                        data_type="str",
                        required=True,
                        description="Message to echo.",
                    ),
                },
            ),
        }
```

Register it:

```toml
[project.entry-points."claia.tool_modules"]
my = "claia.core.tools.modules.my_module:MyModulePlugin"
```

## Use The CLI

Run from source:

```bash
python -m claia.cli
```

Run after installation:

```bash
claia
```

Interactive commands start with `:`. Use `:help`, `:tool`, `:model`, `:agent`, `:prompt`, and `:conversation` to inspect and manage runtime state. One-shot queries and direct tool calls are available through CLI flags and command aliases; run `claia --help` for the current command list.

Configuration can come from CLI flags, interactive `:set`, `.env`, environment variables, and CLI-owned `storage/settings.json`. Plugin settings are discovered from `ParamSpec` declarations, so new providers and tools can add settings without hard-coding CLI flags.
