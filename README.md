# CLAIA Framework

CLAIA is a project I've been working on to abstract away the model loading. Starting it's life as a CLI program (Command Line Artificial Intelligence Agent) and eventually becoming a fully-fledged framework, this project has been designed with modularity and extensibility in mind. The ultimate goal is to have a simple interface that abstracts away the loading of models entirely. The concept is simple, load the registry (which loads the plugins), specify the model you want to run, and voila!

- Website: https://claia.dev  
- License: Apache-2.0  
- Python: 3.12+

## Highlights

- Pluggable architecture using `pluggy` for simple extensibility
- A single `Registry` API for:
  - Models: solve → deploy → run across providers and runtimes
  - Tools: declarative tool modules, protocols, and patterns
  - Agents: process orchestration and worker lifecycle
- Supports models from both API sources as well as local deployments (with plans for remote deployment functionality)
- Robust conversation object with a builtin changelog/audit system

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
python -m claia

# Or after installing
claia
```

Helpful CLI tips (interative mode):
- Type text to chat with the default agent
- Type `:help` for commands
- `:tool` to list tool modules, `:tool <module>` to list commands for a specific module
- `:setup` to set API keys and settings

You can also run CLAIA as a command line utility:

```bash
# Get a list of available commands
claia --help

# Call a tool command directly
claia --tool sample.echo message="Hello"
```

### 2) Use as a library

```python
from claia.registry import Registry
from claia.lib.data import Conversation
from claia.lib.enums.conversation import MessageRole

# Provide credentials or other settings as kwargs (see Configuration)
registry = Registry(openai_api_token="YOUR_OPENAI_API_TOKEN")

conversation = Conversation()
conversation.add_message(MessageRole.USER, "Write a haiku about the moon.")

# Use a canonical model id (definitions map provider-specific identifiers)
result = registry.run("gpt-4", conversation)

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

These values are passed to plugins through the `Registry` and filtered by the plugin’s `required_args`.

## Core Concepts

- Registry: A single facade coordinating models, tools, and agents.  
  Key APIs:
  - `run(model_name, conversation, **kwargs)` — model inference via solver → deployment → architecture
  - `run_command(command_name, parameters, conversation, **kwargs)` — invoke a tool by name
  - Agent processing and worker lifecycle for queued processes
    - `start_workers(total_workers)` — initialize workers to process the queue
    - `stop_workers()` — gracefully terminate all workers
    - `add_process(process: Process)` — add a process to the registry's queue

- Plugin System: Extensions are discovered via Python entry points. Built-in groups include:
  - `claia.architectures` — provider architecture adapters mapping to model classes
  - `claia.deployments` — runtime backends (e.g., API, local)
  - `claia.solvers` — strategies that select deployment/architecture
  - `claia.definitions` — model metadata and canonical IDs (to assist solvers)
  - `claia.agents` — model orchestration strategies
  - `claia.tool_modules` — concrete tool command modules
