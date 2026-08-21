# Plugin Contracts

Shared metadata and configuration contracts for CLAIA extensions. This package tells plugins how to describe themselves without pulling in the framework runtime.

## What Lives Here

- `ExtensionInfo` and specialized info dataclasses for architectures, deployments, definitions, tool protocols, and tool modules.
- `ParamSpec`, `ParamScope`, and `SettingCategory` for declaring plugin settings and runtime parameters.
- `DeploymentParams`, `ToolDefinition`, `ArgumentDefinition`, and `ToolReference` for model and tool execution contracts.
- `COMMON_TEXT_RUNTIME_PARAMS` for common generation parameters such as `temperature`, `max_tokens`, and `stream`.

Agent metadata (`AgentInfo`) lives in `claia.framework.agents.base` because it references `BaseAgent`.

## How It Fits

Plugins expose these dataclasses as a class-level `info` attribute. `claia.framework.Manager` reads the metadata, filters kwargs against `ParamSpec`, masks secrets in logs, and exposes settings to the CLI.

Use `ParamScope.INIT` for values needed when the plugin is constructed, such as API keys and endpoints. Use `ParamScope.RUNTIME` for per-call values, such as generation controls.

```python
from claia.core.plugins.base import ParamScope, ParamSpec, SettingCategory

ParamSpec(
    name="openai_api_token",
    type=str,
    scope=ParamScope.INIT,
    required=True,
    secret=True,
    category=SettingCategory.API,
    description="OpenAI API token.",
)
```
