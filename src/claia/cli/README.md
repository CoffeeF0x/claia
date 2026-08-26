# CLI

One-shot command-line interface and runtime configuration for CLAIA:
`claia <command> [args…]` runs a single command and exits with its
result code.

## What lives here

- `__main__.py` — entrypoint for `python -m claia.cli` / `claia`;
  resolves the invocation (args, piped stdin, bare TTY) and runs one
  command.
- `agents.py` — CLI helpers for creating/running agents and registries.
- `commands/` — subcommand handlers and dispatch.
- `stream/` — stream router: task chunks in, semantic block events out.
- `renderer.py` — `BlockRenderer` (plaintext block-event sink) and
  `PacedRenderer` (TTY-only smooth typing).
- `params.py` — application `ParamSpec` declarations.
- `enums.py` — CLI-only enumerations (`CommandPriority`).
- `defaults.py` — default prompt/settings presets.
- `logger.py` — CLI logging setup.
- `settings.py` — settings model and loading/validation utilities.
- `storage/` — CLI-owned JSON persistence for conversations, prompts,
  and artifacts.
- `utils.py` — CLI utility helpers.

## How CLI fits in (TL;DR)

1. Parse CLI arguments into a config/settings object.
2. Instantiate a `Registry` with filtered kwargs (API keys, paths, etc.).
3. Resolve the invocation: args run as a one-shot command; piped
   stdin becomes an implicit query; a bare TTY prints help; no input
   and no terminal is a usage error (exit 2).
4. Streaming commands wire the task's callbacks to a `StreamRouter`
   and render its block events with `BlockRenderer`.

Custom settings passed via CLI propagate to plugins as filtered kwargs, based on each plugin's declared `ParamSpec` list (plugins only receive kwargs matching a spec they've advertised).

Run from source with `python -m claia.cli`, or use the installed `claia` console script.
