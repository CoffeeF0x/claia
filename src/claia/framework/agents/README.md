# Agents

Agent implementations that orchestrate tasks, models, and tools.

## What lives here

- `simple.py` — `SimpleAgent`, a minimal agent that:
  - reads a `Task` (including `task.parameters["model_id"]` and `task.conversation`)
  - composes `system` (tool-calling instructions prepended to the
    caller persona, or a default helpful-assistant prompt)
  - calls `registry.run(...)` to execute a model
  - parses streaming tags and dispatches tool calls
  - posts tool results as a user `[TOOL_RESULT]` turn and generates
    again until the assistant replies without a tool call
  - marks the task as completed or failed.
- `system.py` — shared prompt composer other agents can reuse.

## How agents fit in

- Agents are discovered via the `claia.agents` entry point, which points at a `BaseAgent` subclass with a class-level `info = AgentInfo(...)`.
- The manager never instantiates agents; it fills `info.agent_class` from the loaded class at discovery.
- Programmatic `Registry.register(...)` still shadows entry-point agents on name conflict.

## When to add/modify an agent

- You need custom orchestration logic (multi-step flows, routing, retries, tooling).
- You want different behavior per agent name (e.g. `"simple"`, `"router"`, `"batch"`).

## Implementing a new agent (TL;DR)

- Subclass `claia.framework.agents.base.BaseAgent` and implement `execute(task, registry, **kwargs)`.
- Declare `info = AgentInfo(name=..., title=..., description=..., params=[...])` on the class. Leave `agent_class` unset — the manager fills it.
- Register the class via the `claia.agents` entry point, or call `registry.register(...)`.
