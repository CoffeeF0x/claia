# Claia Modules

This directory contains modules that extend the functionality of Claia. Each module is a self-contained package that can add new commands, functionality, or integrations to Claia.

## Module Structure

A module must be a directory with the following structure:

```
module_name/
├── __init__.py         # Required: Exports the module's public API
├── commands.py         # Optional: Contains command classes for the module
├── functions.py        # Optional: Contains functions that can be called by the AI
└── ...                 # Other module files
```

### `__init__.py`

The `__init__.py` file should export the module's public API. For example:

```python
"""
Module description
"""

from .some_file import SomeClass

__all__ = ["SomeClass"]
```

### `commands.py`

The `commands.py` file should contain command classes that extend the `Command` base class. For example:

```python
from commands.base import Command
from errors import Result
from settings import Settings

class MyModuleCommand(Command):
    def execute(self, commands: list[str], settings: Settings) -> Result:
        result = Result()
        
        # Command implementation
        
        return result
```

### `functions.py`

The `functions.py` file should contain functions that can be called by the AI. It should also define a `FUNCTION_DEFINITIONS` list that describes the functions in a format compatible with the OpenAI function calling API. For example:

```python
# Define the functions that can be called by the AI
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

def my_function(param1: str, param2: int = 0) -> str:
    """
    Implementation of my_function.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        
    Returns:
        str: Result of the function
    """
    # Function implementation
    return f"Function called with {param1} and {param2}"
```

## Creating a Custom Module

To create a custom module:

1. Create a new directory in the `modules` directory with your module name
2. Create an `__init__.py` file in your module directory
3. Implement your module's functionality
4. If your module adds commands, create a `commands.py` file with your command classes
5. If your module adds functions that can be called by the AI, create a `functions.py` file with your functions and their definitions

## Using Custom Module Directories

You can specify additional directories to search for modules by setting the `CLAIA_MODULE_PATH` environment variable:

```
export CLAIA_MODULE_PATH=/path/to/my/modules:/path/to/more/modules
```

## Disabling Modules

You can disable specific modules by setting the `CLAIA_DISABLED_MODULES` environment variable:

```
export CLAIA_DISABLED_MODULES=module1,module2
```

This will prevent the functions from these modules from being available to the AI.

## Example Modules

- `zammad`: Integration with the Zammad ticketing system 