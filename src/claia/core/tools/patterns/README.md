# Tool Patterns (deprecated — slated for phase 7 removal)

The pattern subsystem was the pre-overhaul tool-call detector for
free-form assistant output. Phase 6 retired its only consumer
(`Registry.process_content`); phase 7 deletes this directory, the
`claia.tool_patterns` entry-point group, and the related
`PatternRegistrar` / hookspec / `Manager` accessors.

## What still lives here (transitionally)

- `default.py` — baseline pattern implementation and utilities. The
  in-tree code no longer constructs or queries it.

## Migration

The streaming [`TagParser`](../../parser/README.md) replaces the
pattern subsystem. Tool-call detection happens inside the agent
loop, and dispatch flows through `Registry.execute_tool` (see
`framework/agents/simple.py` and `tools/protocols/README.md`).
