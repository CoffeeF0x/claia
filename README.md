# CLAIA Framework

CLAIA is a project I've been working on to abstract away the model loading. Starting it's life as a CLI program (Command Line Artificial Intelligence Agent) and eventually becoming a fully-fledged framework, this project has been designed with modularity and extensibility in mind. The ultimate goal is to have a simple interface that abstracts away the loading of models entirely. The concept is simple, load the registry (which loads the plugins), specify the model you want to run, and voila!

- Website: https://claia.dev
- License: Apache-2.0
- Python: 3.12+

## Highlights

- Pluggable architecture using `pluggy` for simple extensibility
- A single `Registry` API for:
  - Models: solve, deploy, and run across providers and runtimes
  - Tools: declarative tool modules and protocols
  - Agents: process orchestration and worker lifecycle
- Supports models from both API sources as well as local deployments (with plans for remote deployment functionality)
- Robust conversation object with a builtin changelog/audit system
- A layered namespace package:
  - `claia.core` contains pure models, plugin contracts, model implementations, definitions, deployments, solvers, and tools.
  - `claia.framework` provides plugin discovery, the `Registry`, process queues, and agent orchestration.
  - `claia.cli` implements the command-line app on top of the framework.

## Documentation

Documentation lives in the ExoFox docs repo under `claia/`. Per-package
READMEs next to the source stay with the code.

## Installation

CLAIA is a Python package targeting Python 3.12+.

Install from source:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .
```

Also available on PyPI and can be installed with:

```bash
pip install claia
```

Note: Some optional model backends (e.g., PyTorch/transformers/diffusers) may have platform-specific requirements. Extended documentation may be available in the future.

## Quickstart

### 1) Use the CLI

```bash
# Run directly from source
python -m claia.cli

# Or after installing
claia
```

Helpful CLI tips (interactive mode):
- Type text to chat with the default agent
- Type `:help` for commands
- `:tool` to list tool modules, `:tool <module>` to list commands for a specific module
- `:setup` to set API keys and settings

You can also run CLAIA as a command line utility:

```bash
# Get a list of available commands
claia --help

# Call a model directly
claia --query "What's the capital of France?"

# Call a tool command directly
claia --tool sample.echo message="Hello"
```

### 2) Use as a library

```python
from claia.framework import Registry, Conversation
from claia.core.enums.conversation import MessageRole

# Provide credentials or other settings as kwargs (see Configuration)
registry = Registry()
registry.load_plugins(openai_api_token="YOUR_OPENAI_API_TOKEN")

conversation = Conversation()
conversation.add_message(MessageRole.USER, "Write a haiku about the moon.")

# Use a canonical model id (definitions map provider-specific identifiers)
result = registry.run("gpt-5.5", conversation)

if result.is_success():
    print(result.get_data())
else:
    print("Error:", result.get_message())
```

## Configuration

CLAIA reads configuration from (in order of precedence):
- CLI flags (e.g., `--openai-api-token`, `--default-agent`)
- CLI set command (--set openai-api-token enter-token-here)
- Interactive set command (:set openai-api-token enter-token-here)
- `.env` file (supports `CLAIA_` prefix in case of conflicts, e.g., `CLAIA_OPENAI_API_TOKEN=...`)
- Environment variables (prefixed or unprefixed)
- A persisted `storage/settings.json` (managed by the CLI)

Note: any configurations found in the environment, .env file, or by using the set command will persist in the settings.json (and may be overwritten according to the precedence order above).

Examples:
- `--openai-api-token YOUR_TOKEN`
- `CLAIA_OPENAI_API_TOKEN=YOUR_TOKEN`

These values are passed to plugins through the `Registry` and filtered by each plugin's declared `ParamSpec` list — plugins only receive the kwargs whose names match a spec they've advertised.

## Core Concepts

- Registry: A single facade coordinating models, tools, and agents.
  Key APIs:
  - `load_plugins(**kwargs)` — discover and initialize registered extensions
  - `run(model_name, conversation, **kwargs)` — model inference via solver, deployment, then architecture
  - `query(model_name, prompt, **kwargs)` — one-shot text prompt helper
  - `run_command(command_name, parameters, conversation, **kwargs)` — invoke a tool by name
  - Agent processing and worker lifecycle for queued processes
    - `start_workers(num_workers)` — initialize workers to process the queue
    - `stop_workers()` — gracefully terminate all workers
    - `add_process(process: Process)` — add a process to the registry's queue

- Plugin System: Extensions are discovered via Python entry points. Built-in groups include:
  - `claia.architectures` — provider architecture adapters mapping to model classes
  - `claia.deployments` — runtime backends (e.g., API, local)
  - `claia.solvers` — strategies that select deployment/architecture
  - `claia.definitions` — model metadata and canonical IDs (to assist solvers)
  - `claia.agents` — model orchestration strategies
  - `claia.tool_modules` — concrete tool command modules
  - `claia.tool_protocols` — protocols that own a tool inventory and execute calls

## Design Philosophy

This section describes how CLAIA is designed and how work moves through the project. It is written for contributors: read it before proposing a change, and use it to judge whether an idea belongs in the library, in a plugin, or if it doesn't belong at all.

### Vision

Running a model should not require understanding how it runs, but it also shouldn't force a project to constrain itself to the vision of the framework. CLAIA exists as a translation layer to abstract the model loading and deployment away from the external project. To achieve this, CLAIA must assume several layers of interfacing, from a granular approach for advanced users to a turnkey approach for higher level use cases. This is achieved by only constraining a contract layer between the consumers (the projects using claia) and enforced on the producers (the modules that interface to the actual model deployments). If this thin layer can be the only enforced structure, this will create a very versatile option in this space.

The framework exists to provide the turnkey solution, which will perhaps introduce the most deliberation. It aims to provide an easy to use option that won't cripple the developer when the project grows. However, it doesn't exist to provide entire production deployment. It currently includes a default agent, a queue system, and a model registry to offer a solution that can be used at a small scale. Any changes to the turnkey offerings should be discussed and approved by both the creator and the community.

Everything that currently exists is built around that goal, however rough the current pieces are. Providers, runtimes, and model families become crutches that make code hard to modify and maintain. CLAIA attempts to dissolve that into a library, allowing the projects to remain flexible, readable, and maintainable.

### Project maturity

CLAIA is pre-alpha. Through this stage and the alpha releases that follow, backward compatibility is explicitly not a goal. Interfaces, names, and contracts change when a better design is found, and they change without deprecation cycles or transitional paths.

This is a deliberate trade. Preserving old interfaces this early produces a codebase shaped by its own history rather than by its current understanding, and every compatibility layer added now is a constraint on a design that has not settled yet. A clean implementation is worth more at this stage than an unbroken upgrade path.

In practice, for contributors:

- When a contract proves wrong, correct it and update every caller. A change that needs a compatibility layer to avoid touching the rest of the tree is a signal to make the change properly instead.
- Removing the old path is part of the work, not a follow-up. Aliases, transitional branches, and dead code do not outlive the change that introduced them.
- Reference plugins, tests, and the CLI move in step with core changes rather than lagging behind them.

Consumers should pin a version and upgrade deliberately; release notes carry the breaking changes. This posture ends as the project approaches a stable release, at which point compatibility becomes a genuine constraint and contract changes earn a deprecation path.

### Principles

#### Modules are the unit of work

CLAIA is a collection of modules held together by thin glue. A module is any self-contained capability with a contract — an architecture, a deployment, a solver, an agent, a tool module, or one of the data structures they exchange. Design, implementation, review, and testing all happen at the module boundary.

The framework layer exists to discover modules and route between them. It grows only when modules need a new seam, never as a home for features that could not find a module to live in. A proposal that only makes sense as glue is a proposal worth re-examining.

#### Nothing is mandatory

Every module must be usable on its own: constructed directly, without the registry, without plugin discovery, without the process queue. A developer should be able to adopt a single piece of CLAIA without inheriting the rest of it. The framework is a convenience, not a requirement, and any change that makes it a requirement is a regression.

#### The core stays small and fenced

Each piece of the core carries one responsibility and an explicit boundary around it. Breadth belongs to plugins; the core provides the contracts that make those plugins interchangeable. When a capability could plausibly live either in the core or in a plugin, it goes in the plugin.

Reference implementations shipped with the library are held to a different standard than plugins: they stay minimal and exemplary, because contributors read them as the model for their own work.

If a piece of the core framework or library becomes, or needs to become, modified in an unintuitive or unreadable way, then that portion of the code should be carefully examined. Both to determine if the code is simply inadequate, or to understand if modification to the overall architecture or design is necessary.

#### Contracts before behavior

Modules communicate through stable, explicit structures rather than through assumptions about each other's internals. Changing a contract is a deliberate act with a wider blast radius than changing an implementation, and should be treated as such in design and review.

#### Behavior is inspectable

A consumer should always be able to determine why CLAIA did what it did — why a backend was selected, why a call failed, what a module was handed. Convenience that hides the mechanism from the caller is not convenience.

#### Consumers do not justify core features

The CLI is CLAIA's first consumer and its living demonstration, not a privileged one. If only the CLI needs something, it belongs to the CLI. The same applies to any other application built on the library.

### Development flow

Every change travels the same path. Stages can be fast, and for a small change most of them are, but they are not skipped.

```
idea -> implementation -> sanity testing -> comprehensive testing -> ci -> deployment testing -> staging -> production
```

#### Idea

Establish scope before writing code. Decide which of four things the idea is: a change to a core contract, a module or plugin, a consumer feature, or something CLAIA should decline to do. Declining is a legitimate and common outcome.

#### Implementation

Build the module against its contract, and make it work standalone before wiring it into the framework. If it cannot be exercised without the registry, it is not finished.

#### Sanity testing

Hands-on human validation. The sanity module/folder under claia is a space for simple validation, and is disposable by design. The code is minimal and readable, and edge cases are explicitly not its concern. It answers "does this behave the way I expect when I use it?" — a simple validation process with an easily modifiable design quickly adapt for your own validation.

The sanity folder is not a comprehensive test suite and must never grow into one.

#### Comprehensive testing

The permanent, comprehensive test layer, and the first stage that runs without a human in the loop. Two conventions keep it navigable:

- **Tests mirror the source tree.** A module at `src/claia/core/solvers/default.py` is tested at `src/tests/core/solvers/default.py`. Directory names match, and files carry no `test_` prefix.
- **Shared fixtures, fakes, and builders live in `src/tests/mocks/`.** Tests do not define their own, which keeps the structures under test consistent across the suite.

Tests are modular in the same way the source is: each file covers its counterpart's contract and the edge cases sanity testing deliberately ignored.

#### CI

The automated pipeline. It runs the test suite and, on success, produces the packages and images the later stages consume. CI is the boundary between a change that works on one machine and a change that works.

#### Deployment testing

A post deployment, manual verification step against real artifacts, built outside an active development environment. Testers install the built packages into clean environments and exercise them as a user would, which catches the class of problem that only appears once packaging, dependencies, and installation are involved. This step is necessary for any versioned release.

#### Staging

Pre-production validation, where release candidates are available for early testing and inspection.

#### Production

The release. If the preceding stages were done honestly, this stage will be uneventful. Which above all else, is the goal of this exhaustive pipeline.
