# Claia Tools Module

This module provides function calling capabilities for AI models in Claia. It includes a set of tools that can be called by the AI and a function calling prompt that instructs the AI on how to use these tools.

## Overview

The tools module consists of:

1. `__init__.py` - Main module file that exports functions and provides the function calling prompt
2. `functions.py` - Contains the tool functions and their definitions

## Function Calling Format

The AI uses the following format to call functions:

```
[FUNCTION_CALL]{
"name": "function_name",
"parameters": {
  "param1": "value1",
  "param2": "value2"
}
}[/FUNCTION_CALL]
```

## Available Tools

The following tools are available:

- `get_current_time()` - Returns the current time in HH:MM:SS format
- `get_current_date()` - Returns the current date in YYYY-MM-DD format
- `get_user_name()` - Returns a hardcoded user name
- `greet_user(name)` - Greets a user by name

## Adding New Tools

To add a new tool:

1. Add the function to `functions.py`
2. Add the function definition to the `FUNCTION_DEFINITIONS` list in `functions.py`
3. Add the function to the `get_functions()` dictionary in `__init__.py`
4. Add the function to the `__all__` list in `__init__.py`

Example:

```python
# In functions.py
def my_new_function(param1: str, param2: int) -> str:
    """
    Description of my new function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        str: Description of return value
    """
    return f"Processed {param1} and {param2}"

# Add to FUNCTION_DEFINITIONS
{
    "name": "my_new_function",
    "description": "Description of my new function",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description of param1"
            },
            "param2": {
                "type": "integer",
                "description": "Description of param2"
            }
        },
        "required": ["param1", "param2"]
    },
    "returns": {
        "type": "string",
        "description": "Description of return value"
    }
}

# In __init__.py, update get_functions()
def get_functions() -> Dict[str, Callable]:
    return {
        # ... existing functions ...
        "my_new_function": my_new_function
    }

# In __init__.py, update __all__
__all__ = [
    # ... existing exports ...
    "my_new_function"
]
```

## Integration with Module System

The tools module works alongside the module system. When a function call is detected:

1. First, the system checks if the function exists in the tools module
2. If not found, it checks if the function exists in any loaded modules
3. If still not found, it returns an error message

This allows for both core tools and module-specific functions to be called by the AI. 