# CLI

Command-line interface and runtime configuration for CLAIA.

## What lives here

- `__main__.py` — entrypoint for `python -m claia.cli` / `claia`.
- `agents.py` — CLI helpers for creating/running agents and registries.
- `commands/` — subcommands and interactive flows.
- `defaults.py` — default prompt/settings presets.
- `logger.py` — CLI logging setup.
- `renderer.py` — terminal output formatting.
- `settings.py` — settings model and loading/validation utilities.
- `storage/` — CLI-owned JSON persistence for conversations, prompts, and artifacts.
- `utils.py` — CLI utility helpers.

## How CLI fits in (TL;DR)

1. Parse CLI arguments into a config/settings object.
2. Instantiate a `Registry` with filtered kwargs (API keys, paths, etc.).
3. Create conversations/tasks and dispatch them to agents/models.

Custom settings passed via CLI propagate to plugins as filtered kwargs, based on each plugin's declared `ParamSpec` list (plugins only receive kwargs matching a spec they've advertised).

Run from source with `python -m claia.cli`, or use the installed `claia` console script.
