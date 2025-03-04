# Claia Modules

This directory contains modules that extend the functionality of Claia. Each module is a self-contained package that can add new commands and functions to Claia.

## Overview

Modules are loaded dynamically at runtime and can:
1. Add new commands to the command system
2. Provide functions that can be called by AI models
3. Extend existing functionality with new features

## Module Structure

A module must be a directory with the following structure:

```
module_name/               # The directory name becomes the command name
├── module.py              # Required: Contains the module implementation
└── README.md              # Optional: Documentation for the module
```

The `module.py` file must contain one or both of the following:

1. A `ModuleCommands` class that inherits from `commands.base.Command`
2. A `FUNCTION_DEFINITIONS` list of function definitions

## Commands

To add commands, your module must define a `ModuleCommands` class in `module.py`:

```python
from commands.base import Command
from errors import Result
from settings import Settings

class ModuleCommands(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    # Command implementation
    return Result(success=True, message="Command executed!")
    
  def help(self) -> str:
    # Help information for the command
    return "module_name - Description of what this module does"
```

The command will be available using the module's directory name:

```
:module_name arg1 arg2
```

## Functions

To add functions that can be called by AI models, your module must define a `FUNCTION_DEFINITIONS` list in `module.py`:

```python
def my_function(param1: str, param2: int = 0) -> str:
  # Function implementation
  return f"Function called with {param1} and {param2}"

FUNCTION_DEFINITIONS = [
  {
    "name": "my_function",
    "description": "Description of what the function does",
    "parameters": {
      "type": "object",
      "properties": {
        "param1": {
          "type": "string",
          "description": "Description of parameter 1"
        },
        "param2": {
          "type": "integer",
          "description": "Description of parameter 2"
        }
      },
      "required": ["param1"]
    }
  }
]
```

Functions can then be called by AI models using:

```
[FUNCTION_CALL]
{
  "name": "my_function",
  "parameters": {
    "param1": "value1",
    "param2": 42
  }
}
[/FUNCTION_CALL]
```

## Creating a Module

To create a new module:

1. Create a new directory in the `modules` directory
2. Create a `module.py` file in your module directory
3. Implement your `ModuleCommands` class and/or functions
4. Add a `README.md` file with documentation for your module

See the `sample` directory for a complete example of a module with both commands and functions.

## Module Loading Process

The module loading process is as follows:

1. The application calls `modules.load(settings)` during startup
2. The `load` function gets the modules directory from settings
3. It iterates through each subdirectory in the modules directory
4. For each subdirectory, it looks for a `module.py` file
5. If found, it checks if the module has a `ModuleCommands` class and/or `FUNCTION_DEFINITIONS` list
6. Module names are added to `settings.command_modules` and/or `settings.function_modules` lists for lazy loading
7. Modules are only fully loaded when their commands or functions are actually needed

## Lazy Loading

The module system uses lazy loading to improve performance:

1. During startup, only the names of modules are registered, not the actual module contents
2. When a command is executed, the corresponding module is loaded on-demand
3. When functions are needed, they are loaded from the modules on-demand
4. This reduces memory usage and startup time, especially for applications with many modules

## Error Handling

The module system will:

1. Log errors if the modules directory is not defined or doesn't exist
2. Skip modules that don't have a `module.py` file
3. Log errors if a module fails to load
4. Continue loading other modules even if some fail
