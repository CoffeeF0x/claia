# Experimental Module

This module contains experimental features and test functions for Claia.

## Features

### Functions

The module provides the following functions that can be called by the AI:

- `get_current_time()`: Returns the current time in HH:MM:SS format
- `get_current_date()`: Returns the current date in YYYY-MM-DD format
- `get_user_name()`: Returns a hardcoded user name
- `greet_user(name)`: Greets a user by name

### Commands

The module provides the following commands:

- `experimental test`: Tests Stable Diffusion image generation
- `experimental mini`: Tests the MiniCPM3 model
- `experimental function`: Tests function calling capabilities

## Usage

### Function Calling

The functions in this module can be called by the AI using the function calling format:

```
[FUNCTION_CALL]
{
  "name": "experimental_get_current_time",
  "parameters": {}
}
[/FUNCTION_CALL]
```

### Commands

To use the experimental commands, type:

```
:experimental test
:experimental mini
:experimental function
```

## Requirements

- For `experimental test`: Requires PyTorch and the diffusers library
- For `experimental mini`: Requires PyTorch and the transformers library 