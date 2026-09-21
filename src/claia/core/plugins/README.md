# Plugin Contracts

Shared metadata and configuration contracts for CLAIA extensions. This package tells plugins how to describe themselves without pulling in the framework runtime.

## What Lives Here

- `ExtensionInfo` and specialized info dataclasses for architectures, deployments, nodes, definitions, tool protocols, and tool modules.
- `ParamSpec`, `ParamScope`, and `ParamCategory` for declaring plugin settings and runtime parameters.
- `ServingPlan`, `ToolDefinition`, `ArgumentDefinition`, and `ToolReference` for model and tool execution contracts.
- `COMMON_TEXT_RUNTIME_PARAMS` for common generation parameters such as `temperature`, `max_tokens`, and `stream`.
- `API_OPTIONAL_SAMPLING_PARAMS`, `API_MAX_TOKENS_PARAM`, and `EFFORT_PARAM` for hosted APIs: sampling is omitted unless set, and `effort` is the shared reasoning/thinking knob.

Agent metadata (`AgentInfo`) lives in `claia.framework.agents.base` because it references `BaseAgent`.

## How It Fits

Plugins expose these dataclasses as a class-level `info` attribute. `claia.framework.Manager` reads the metadata, filters kwargs against `ParamSpec`, masks secrets in logs, and exposes settings to the CLI.

Use `ParamScope.INIT` for values needed when the plugin is constructed, such as API keys and endpoints. Use `ParamScope.RUNTIME` for per-call values, such as generation controls.

```python
from claia.core.enums.plugins import ParamScope, ParamCategory
from claia.core.plugins.base import ParamSpec

ParamSpec(
    name="openai_api_token",
    type=str,
    scope=ParamScope.INIT,
    required=True,
    secret=True,
    category=ParamCategory.API,
    description="OpenAI API token.",
)
```
