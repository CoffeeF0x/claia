# Framework

The framework layer is CLAIA's orchestration runtime. It loads plugins, exposes the `Registry` facade, runs tools and models, and manages agent processes.

## What Lives Here

- `manager.py` — discovers entry-point plugins via `importlib.metadata` and instantiates them.
- `registry.py` — the app-facing composition root for models, tools, and agents.
- `process.py` and `queue.py` — units of work and queueing for agents.
- `agents/` — base agent contract and built-in agent plugins.

## Runtime Flow

1. The CLI or host app builds settings.
2. `Registry.load_plugins(**kwargs)` asks `Manager` to discover entry points and initialize extensions.
3. Model calls resolve a deployment and architecture, then run through those plugins.
4. Tool calls flow through protocol and module plugins.
5. Agent work is represented as `Process` objects and can be handled directly or by registry workers.

## Library Entry Point

```python
from claia.framework import Registry, Conversation

registry = Registry()
registry.load_plugins(openai_api_token="sk-...")

conversation = Conversation()
conversation.add_message("user", "Hello!")

result = registry.run("gpt-4", conversation)
print(result.get_data())
```

Because `claia` is a namespace package, `claia.framework` also acts as a convenience hub. It re-exports common `claia.core` types such as `Conversation`, `Result`, `ParamSpec`, `ModelDefinition`, and chunk classes.

Run the CLI with `python -m claia.cli` from source or `claia` after installation.
