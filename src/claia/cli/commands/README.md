# CLI Commands

Command handlers for CLAIA's interactive REPL and command-line flags. This package turns parsed tokens into settings changes, model calls, tool calls, and conversation operations.

## What Lives Here

- `core.py` — `Commands`, the dispatcher that maps aliases to command classes and runs one or more commands.
- `specs.py` — command aliases, help text, conversation requirements, and execution priority.
- `base.py` — `BaseCommand`, shared command interface and formatting helpers.
- `system.py` — quit, version, and help commands.
- `get_set.py` — get, set, and reset settings commands.
- `query.py`, `tool.py`, `model.py`, `agent.py`, and `conversation.py` — runtime operations.
- `setup.py` — interactive setup wizard for missing settings.
- `extension.py` — CLI tool module exposed to the framework's tool catalog.

## How It Fits

The CLI builds a `Commands` dispatcher with the active `Registry` and settings object. Interactive commands are prefixed with `:`, while installed CLI flags use aliases generated from the same command specs.

Add a command by implementing `BaseCommand`, registering it in `Commands._build_command_maps()`, and adding aliases/help metadata to `COMMAND_SPECS`.
