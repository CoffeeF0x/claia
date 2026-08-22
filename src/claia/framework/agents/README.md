# Agents

Agent implementations that orchestrate tasks, models, and tools.

## What lives here

- `base.py` — `BaseAgent`, the shared generate loop: compose `system`
  (tool instructions prepended to a pinned `SYSTEM_PROMPT`, the
  caller persona, or a default), stream `registry.run`, parse tags,
  dispatch tools, post a user `[TOOL_RESULT]` turn, and generate
  again until the assistant replies without a tool call.
- `simple.py` — `SimpleAgent`, the default registered agent. Uses
  `BaseAgent.execute` as-is.

## How agents fit in

- Agents are discovered via the `claia.agents` entry point, which points at a `BaseAgent` subclass with a class-level `info = AgentInfo(...)`.
- The manager never instantiates agents; it fills `info.agent_class` from the loaded class at discovery.
- Programmatic `Registry.register(...)` still shadows entry-point agents on name conflict.
- Host agents (CLI `writer`, Slate Bob) pin `SYSTEM_PROMPT` and inherit the loop. Agents that are not a chat turn (Slate's conversation namer) override `execute`.

## When to add/modify an agent

- You need a different persona — set `SYSTEM_PROMPT`.
- You need custom orchestration (routing, one-shot side effects) — override `execute`.

## Implementing a new agent (TL;DR)

- Subclass `claia.framework.agents.base.BaseAgent`. Pin `SYSTEM_PROMPT` or override `execute(task, registry, **kwargs)`.
- Declare `info = AgentInfo(name=..., title=..., description=..., params=[...])` on the class. Leave `agent_class` unset — the manager fills it.
- Register the class via the `claia.agents` entry point, or call `registry.register(...)`.
