# Agents

Agent implementations that orchestrate tasks, models, and tools.

## What lives here

- `base.py` — `BaseAgent` utilities: compose `system`, stream one
  assistant turn (`stream_turn`), parse tags, dispatch tools, post a
  user `[TOOL_RESULT]`. `execute` is abstract.
- `simple.py` — `SimpleAgent`, the default registered agent. Reads
  `system` from the call or the queued task, composes tool
  instructions, and owns the generate-again loop.

## How agents fit in

- Agents are discovered via the `claia.agents` entry point, which points at a `BaseAgent` subclass with a class-level `info = AgentInfo(...)`.
- The manager never instantiates agents; it fills `info.agent_class` from the loaded class at discovery.
- Programmatic `Registry.register(...)` still shadows entry-point agents on name conflict.
- Host agents (CLI `writer`, Slate Bob) implement `execute`: they pick a persona, compose `system`, and run the same loop. Agents that are not a chat turn (Slate's conversation namer) implement a different `execute`.

## When to add/modify an agent

- You need a different persona or task-parameter mapping — implement `execute`.
- You need custom orchestration (routing, one-shot side effects) — implement `execute`.

## Implementing a new agent (TL;DR)

- Subclass `claia.framework.agents.base.BaseAgent` and implement `execute(task, registry, **kwargs)`.
- Read `model_id` / `system` from the task (or pass your own persona into `compose_system_prompt`), then call `stream_turn` / `_post_tool_results` as needed.
- Declare `info = AgentInfo(name=..., title=..., description=..., params=[...])` on the class. Leave `agent_class` unset — the manager fills it.
- Register the class via the `claia.agents` entry point, or call `registry.register(...)`.
