# Extension Strategy
(thought: dynamic loading is required for the agents and the cli, the more library style modules shouldn't need to import anything during runtime)


## Current Architecture Analysis

### Existing Extension Systems
1. **Agent Extensions** - Custom agents in `/src/extensions/{name}/agent.py`
2. **Command Extensions** - Custom commands in `/src/extensions/{name}/command.py`
3. **Model Extensions** - Built into models package with manual imports
4. **Dynamic Loading** - Runtime import discovery in `src/mod.py`

### Problems with Current Approach
- Multiple different discovery mechanisms
- Manual import management for models
- Complex dynamic loading with `sys.path` manipulation
- Inconsistent registration patterns
- Tight coupling between core and extensions

## Proposed Extension Framework

### 1. Plugin Registry Pattern
Create a unified `PluginRegistry` that manages all extension types:

```python
class PluginRegistry:
    def __init__(self):
        self.agents = {}
        self.commands = {}
        self.models = {}

    def register_agent(self, name: str, agent_class):
        self.agents[name] = agent_class

    def register_command(self, name: str, command_class):
        self.commands[name] = command_class

    def register_model(self, name: str, model_class):
        self.models[name] = model_class
```

### 2. Decorator-Based Registration
Use decorators for simple, declarative extension registration:

```python
from claia.extensions import register_agent, register_command, register_model

@register_agent("bob")
class BobAgent(BaseAgent):
    pass

@register_command("hello")
class HelloCommand(BaseCommand):
    pass

@register_model("custom-gpt")
class CustomGPTModel(APIModel):
    pass
```

### 3. Entry Points System
Use Python entry points for discovery (similar to pytest plugins):

```toml
# In extension's pyproject.toml
[project.entry-points."claia.agents"]
bob = "my_extension.agents:BobAgent"

[project.entry-points."claia.commands"]
hello = "my_extension.commands:HelloCommand"

[project.entry-points."claia.models"]
custom-gpt = "my_extension.models:CustomGPTModel"
```

### 4. Extension Interface Classes
Define clear interfaces for each extension type:

```python
class ExtensionAgent(Protocol):
    def process_request(self, process: Process) -> Process:
        ...

class ExtensionCommand(Protocol):
    def execute(self, settings: Settings, **kwargs) -> Result:
        ...

class ExtensionModel(Protocol):
    def generate(self, conversation: Conversation) -> Result:
        ...
```

## Implementation Options

### Option A: Entry Points + Decorators (Recommended)
**Pros:**
- Industry standard (used by pytest, flask, etc.)
- Automatic discovery without sys.path manipulation
- Clean extension development experience
- Supports both internal and external extensions

**Cons:**
- Requires pip install for extension activation
- Slightly more complex for simple internal extensions

### Option B: Directory Scanning + Decorators
**Pros:**
- Simple for internal extensions
- No installation required
- Similar to current approach but cleaner

**Cons:**
- Still requires sys.path manipulation
- No support for external extensions
- Discovery logic in core

### Option C: Hybrid Approach
**Pros:**
- Entry points for external extensions
- Directory scanning for internal modules
- Best of both worlds

**Cons:**
- More complex implementation
- Two discovery mechanisms to maintain

## Recommended Implementation

### Phase 1: Unified Registration
1. Create `ExtensionRegistry` class
2. Create registration decorators
3. Migrate existing modules to use decorators

### Phase 2: Entry Points Discovery
1. Add entry points support
2. Create extension template/cookiecutter
3. Document extension development

### Phase 3: Clean Interfaces
1. Define formal extension protocols
2. Add validation and error handling
3. Create extension testing framework

## Extension Development Experience

### For Simple Internal Extensions:
```python
# modules/hello/extension.py
from claia.extensions import register_command
from claia.commands import BaseCommand

@register_command("hello")
class HelloCommand(BaseCommand):
    def execute(self, settings, **kwargs):
        return Result(message="Hello World!")
```

### For Complex External Extensions:
```python
# my-claia-extension/setup.py
setup(
    name="my-claia-extension",
    entry_points={
        "claia.agents": ["custom = my_extension:CustomAgent"],
        "claia.commands": ["tool = my_extension:ToolCommand"],
    }
)
```

## Migration Strategy

1. **Preserve Current System** - Keep existing loading during transition
2. **Add New Registry** - Implement alongside current system
3. **Migrate Incrementally** - Update one module at a time
4. **Remove Old System** - Clean up after all modules migrated
5. **External Support** - Add entry points after internal migration complete
