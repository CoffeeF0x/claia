# Agents

Agent implementations that orchestrate processes, models, and tools.

## What lives here

- `simple.py` — `SimpleAgent`, a minimal agent that:
  - reads a `Process` (including `process.parameters["model_id"]` and `process.conversation`)
  - calls `registry.run(...)` to execute a model
  - marks the process as completed or failed.

## How agents fit in

- Agents are discovered via the `claia.agents` pluggy entry point.
- The `Manager` and `Registry` use agent plugins to decide **how** to run work:
  - which model to call
  - how to update processes and conversations
  - how to report results.

## When to add/modify an agent

- You need custom orchestration logic (multi-step flows, routing, retries, tooling).
- You want different behavior per agent name (e.g. `"simple"`, `"router"`, `"batch"`).

## Implementing a new agent (TL;DR)

- Subclass `claia.framework.agents.base.BaseAgent` and implement a class method like `process_request(process, registry, **kwargs)`.
- Provide a plugin class implementing the hooks in `claia.framework.hooks.agent`:
  - `get_agent_class(agent_name) -> Type[BaseAgent]`
  - `get_agent_info() -> AgentInfo` (name, description, `params: List[ParamSpec]`).
