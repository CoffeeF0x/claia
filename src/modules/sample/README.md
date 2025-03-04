# Sample Module

This is a sample module for the CLAI application that demonstrates how to create modules with both commands and functions.

## Commands

The module provides a command named after the folder name (`sample_module`).

Example usage:
```
sample_module arg1 arg2
```

## Functions

The module provides the following functions:

- `sample_function`: A sample function that demonstrates module functionality

Function parameters:
- `text`: Text to process

## Module Structure

A valid CLAI module must:

1. Be placed in a subdirectory of the modules directory (the directory name becomes the command name)
2. Contain a `module.py` file
3. Implement a `ModuleCommands` class and/or export `FUNCTION_DEFINITIONS` list

### ModuleCommands

The `ModuleCommands` class must inherit from `commands.base.Command` and implement:

- `execute(commands: list[str], settings: Settings) -> Result`: Execute the command
- `help() -> str`: Return help information for the command

### FUNCTION_DEFINITIONS

The `FUNCTION_DEFINITIONS` list should contain function definition dictionaries with the following structure:

```python
{
  "name": "function_name",
  "description": "Function description",
  "parameters": {
    "type": "object",
    "properties": {
      "param_name": {
        "type": "param_type",
        "description": "Parameter description"
      }
    },
    "required": ["required_param_names"]
  },
  "function": actual_function_reference
}
```

The `function` key should reference the actual function to be called, which should accept a dictionary of parameters and return a dictionary result. 