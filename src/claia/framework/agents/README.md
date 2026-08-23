# Agents

Agent implementations that orchestrate tasks, models, and tools.

## What lives here

- `base.py` — the step contract and shared utilities. `step` is
  abstract (one unit of work, reported as an `AgentStatus`); `run`
  drives one step per call and applies the status to the task;
  `execute` drives steps to completion synchronously for direct,
  queue-less use. Utilities: `chat_step` (one tool-loop turn),
  `compose_system_prompt`, `stream_turn`, tag parsing, tool dispatch,
  attaching result `ToolArtifact`s onto TOOL utilities.
- `simple.py` — `SimpleAgent`, the default registered agent. Reads
  `system` from the call or the queued task and runs one `chat_step`
  per step.

## How agents fit in

- Agents are discovered via the `claia.agents` entry point, which points at a `BaseAgent` subclass with a class-level `info = AgentInfo(...)`.
- The manager never instantiates agents; it fills `info.agent_class` from the loaded class at discovery.
- Programmatic `Registry.register(...)` still shadows entry-point agents on name conflict.
- The queue worker runs **one step per dispatch**: a step reporting `AgentStatus.CONTINUE` leaves the task `PENDING` and the registry re-enqueues it, so queued tasks interleave fairly and cancellation applies between steps.
- Loop state lives in `task.parameters` (the chat loop keeps its round counter under `BaseAgent.ROUND_PARAMETER`), so it survives re-enqueues and stays externally visible and editable.
- Host agents (CLI `writer`, Slate Bob) pass their persona to `chat_step`. One-shot agents (Slate's conversation namer) do their work in a single step and return a terminal status.

## When to add/modify an agent

- You need a different persona — implement `step` as a one-line `chat_step` call with your `system`.
- You need custom orchestration (routing, one-shot side effects, multi-phase work) — implement `step`; return `CONTINUE` to get another step later, or a terminal `AgentStatus` to end the task.

## Implementing a new agent (TL;DR)

- Subclass `claia.framework.agents.base.BaseAgent` and implement `step(task, registry, **kwargs) -> AgentStatus`.
- Set `task.result` / `task.error` before returning a terminal status — the framework owns the actual task state transition (`mark_*`).
- Keep any state your next step needs in `task.parameters`; dispatch merges those parameters into your step's kwargs, so pop keys you don't want forwarded to the model call (`chat_step` already drops `model_id` and the round counter).
- Declare `info = AgentInfo(name=..., title=..., description=..., params=[...])` on the class. Leave `agent_class` unset — the manager fills it.
- Register the class via the `claia.agents` entry point, or call `registry.register(...)`.
