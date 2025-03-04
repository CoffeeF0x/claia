"""
Tools module for Claia

This module provides function calling capabilities for AI models.
It includes function calling prompt generation and execution.
"""

# External dependencies
import json
import importlib
from typing import Dict, Any, List, Callable, Optional

# Internal dependencies
from commands import get_function_definitions, execute_command_by_name
from file import LLMPromptStore
from settings import Settings



##################################################
#                   CONSTANTS                    #
##################################################
# Function calling format
FUNCTION_FORMAT = """
[FUNCTION_CALL]{
"name": "function_name",
"parameters": {
  "param1": "value1",
  "param2": "value2"
}
}[/FUNCTION_CALL]
"""

# Function calling prompt template
FUNCTION_CALLING_PROMPT = """
You are an AI assistant capable of calling functions. Here are the available functions:

{function_definitions}

When you need to call a function, use the following format:
{function_format}

You can call multiple functions in a single response if needed. Each function call will be replaced with its result.
Incorporate the function call(s) into your response where necessary.
"""



##################################################
#              FUNCTION EXECUTION                #
##################################################
def execute_function(function_name: str, function_call: Dict[str, Any], settings=None) -> str:
  """
  Execute a function by name with the given parameters.

  Args:
    function_name: Name of the function to execute
    function_call: Dictionary containing function call details
    settings: Optional settings object

  Returns:
    str: Result of the function call or error message
  """
  try:
    # Call the function with parameters
    if "parameters" in function_call:
      return execute_command_by_name(function_name, function_call["parameters"], settings)
    else:
      return execute_command_by_name(function_name, {}, settings)
  except Exception as e:
    return f"Error executing function {function_name}: {str(e)}"

def process_function_calls(response: str, settings=None) -> str:
  """
  Process any function calls in the model response.
  Replaces each function call with its result, preserving the rest of the response.
  Supports multiple function calls in a single response.

  Args:
    response: The model response to process
    settings: Optional settings object

  Returns:
    str: The processed response with function calls replaced by their results
  """
  if not response or "[FUNCTION_CALL]" not in response:
    return response

  # Get min and max function calls from settings
  min_calls = 5  # Default minimum
  max_calls = 10  # Default maximum
  if settings:
    min_calls = getattr(settings, 'min_function_calls', min_calls)
    max_calls = getattr(settings, 'max_function_calls', max_calls)

  processed_response = response
  call_count = 0

  # Process function calls until we reach the maximum or no more calls are found
  while "[FUNCTION_CALL]" in processed_response and call_count < max_calls:
    try:
      # Find all function calls in the response
      start_marker = "[FUNCTION_CALL]"
      end_marker = "[/FUNCTION_CALL]"

      # Find all start and end positions
      start_positions = []
      end_positions = []
      pos = 0

      while True:
        start_pos = processed_response.find(start_marker, pos)
        if start_pos == -1:
          break
        start_positions.append(start_pos)
        pos = start_pos + len(start_marker)

      pos = 0
      while True:
        end_pos = processed_response.find(end_marker, pos)
        if end_pos == -1:
          break
        end_positions.append(end_pos + len(end_marker))
        pos = end_pos + len(end_marker)

      # If no valid function calls found, break
      if not start_positions or not end_positions or len(start_positions) != len(end_positions):
        break

      # Process function calls from innermost to outermost
      # Find the innermost function call (one with no other start markers between its start and end)
      innermost_idx = None
      for i, start_pos in enumerate(start_positions):
        end_pos = end_positions[i]
        # Check if there's another start marker between this start and end
        has_nested = any(pos > start_pos and pos < end_pos for pos in start_positions)
        if not has_nested:
          innermost_idx = i
          break

      if innermost_idx is None:
        # Something is wrong with the function call format
        break

      # Extract the innermost function call
      start_pos = start_positions[innermost_idx]
      end_pos = end_positions[innermost_idx]
      function_call_str = processed_response[start_pos + len(start_marker):end_pos - len(end_marker)]
      full_function_call = processed_response[start_pos:end_pos]

      # Parse the function call
      function_call = json.loads(function_call_str)
      function_name = function_call["name"]

      # Execute the function
      result = execute_function(function_name, function_call, settings)

      # Replace the function call with its result
      processed_response = processed_response.replace(full_function_call, result)

      call_count += 1

      # If we've processed the minimum number of calls and there are no more, break
      if call_count >= min_calls and "[FUNCTION_CALL]" not in processed_response:
        break

    except Exception as e:
      # If there's an error processing the function call, add an error message
      # but continue processing other function calls
      error_msg = f"Error processing function call: {str(e)}"
      if 'start_pos' in locals() and 'end_pos' in locals():
        processed_response = processed_response.replace(
          processed_response[start_pos:end_pos],
          error_msg
        )
      else:
        # If we can't identify the specific function call with the error,
        # just append the error message and break
        processed_response += f"\n\n{error_msg}"
        break

  return processed_response



##################################################
#                PROMPT GENERATION               #
##################################################
def get_function_calling_prompt(settings=None) -> str:
  """
  Get the function calling prompt with all available function definitions.

  Args:
    settings: Optional settings object

  Returns:
    str: The function calling prompt
  """
  try:
    # Get function definitions from commands
    function_definitions = get_function_definitions(settings)
    
    # Debug output
    print(f"Found {len(function_definitions)} function definitions")
    
    # Convert to JSON with proper indentation
    function_definitions_json = json.dumps(function_definitions, indent=2)
    
    # Format the prompt
    return FUNCTION_CALLING_PROMPT.format(
      function_definitions=function_definitions_json,
      function_format=FUNCTION_FORMAT
    )
  except Exception as e:
    print(f"Error generating function calling prompt: {str(e)}")
    # Return a basic prompt with no functions in case of error
    return FUNCTION_CALLING_PROMPT.format(
      function_definitions="[]",
      function_format=FUNCTION_FORMAT
    )

def add_function_calling_prompt_to_store(settings) -> None:
  """
  Adds the function calling prompt to the prompt store in the settings object.

  Args:
    settings: The settings object containing the prompt store
  """
  if settings is None:
    return
    
  function_calling_prompt_name = "functions"

  # Check if prompt already exists
  if not settings.prompt_exists(function_calling_prompt_name):
    try:
      # Get the function calling prompt
      function_calling_prompt = get_function_calling_prompt(settings)

      # Add to prompt store
      settings.prompt_store.append(
        LLMPromptStore(
          settings.prompt_store_directory,
          function_calling_prompt_name,
          "Function Calling Assistant",
          function_calling_prompt,
          "An assistant capable of calling functions."
        )
      )
    except Exception as e:
      print(f"Error adding function calling prompt to store: {str(e)}")


##################################################
#                 DEBUG FUNCTIONS                #
##################################################
def debug_function_definitions(settings=None) -> None:
  """
  Print debug information about function definitions.
  
  Args:
    settings: Optional settings object
  """
  try:
    from commands import get_enabled_command_instances
    
    print("Debugging function definitions:")
    
    # Get all enabled command instances
    command_instances = get_enabled_command_instances()
    print(f"Found {len(command_instances)} enabled command instances:")
    
    # Check each command instance
    for i, cmd_instance in enumerate(command_instances):
      print(f"\n{i+1}. Command instance: {cmd_instance.__class__.__name__}")
      
      # Check if it has the get_function_definitions method
      if hasattr(cmd_instance, 'get_function_definitions'):
        print(f"  - Has get_function_definitions method: Yes")
        
        # Check the function tree
        if hasattr(cmd_instance, 'function_tree'):
          print(f"  - Function tree size: {len(cmd_instance.function_tree)}")
          
          # Print the top-level keys in the function tree
          print(f"  - Function tree top-level keys: {list(cmd_instance.function_tree.keys())}")
          
          # Try to get function definitions
          try:
            func_defs = cmd_instance.get_function_definitions()
            print(f"  - Function definitions count: {len(func_defs)}")
          except Exception as e:
            print(f"  - Error getting function definitions: {str(e)}")
        else:
          print(f"  - Function tree: Not found")
      else:
        print(f"  - Has get_function_definitions method: No")
  except Exception as e:
    print(f"Error in debug_function_definitions: {str(e)}")


# Export the functions
__all__ = [
  # Function execution
  "execute_function",
  "process_function_calls",

  # Prompt generation
  "get_function_calling_prompt",
  "add_function_calling_prompt_to_store",

  # Debug functions
  "debug_function_definitions"
] 