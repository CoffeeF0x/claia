"""
Tools module for Claia

This module provides function calling capabilities for AI models.
It includes the function calling prompt and tools that can be called by the AI.
"""

import json
import importlib
from typing import Dict, Any, List, Callable

# Import tool functions
from tools.functions import (
  get_current_time,
  get_current_date,
  get_user_name,
  greet_user,
  FUNCTION_DEFINITIONS
)



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

<CURRENT_CURSOR_POSITION>
When you need to call a function, use the following format:
{function_format}

You can call multiple functions in a single response if needed. Each function call will be replaced with its result.
Incorporate the function call(s) into your response where necessary.
"""
# Respond to the user's request by calling the appropriate function when necessary.
# """

# Module system availability flag
HAS_MODULE_SYSTEM = False

# Try to check if modules are available without importing the full module
try:
  spec = importlib.util.find_spec('modules')
  HAS_MODULE_SYSTEM = spec is not None
except:
  pass



##################################################
#                 CORE FUNCTIONS                 #
##################################################
def get_functions() -> Dict[str, Callable]:
  """
  Get all available tool functions.

  Returns:
    Dict[str, Callable]: Dictionary of function names to function objects
  """
  return {
    "get_current_time": get_current_time,
    "get_current_date": get_current_date,
    "get_user_name": get_user_name,
    "greet_user": greet_user
  }



##################################################
#               FUNCTION DISCOVERY               #
##################################################
def get_function_definitions(settings=None) -> List[Dict[str, Any]]:
  """
  Get all function definitions from both tools and modules.

  Args:
    settings: Optional settings object to check if modules are enabled

  Returns:
    List[Dict[str, Any]]: Combined list of function definitions
  """
  all_definitions = list(FUNCTION_DEFINITIONS)
  
  # Add module definitions if available
  if HAS_MODULE_SYSTEM and settings:
    # Access module_function_definitions directly from settings if available
    if hasattr(settings, 'module_function_definitions') and settings.module_function_definitions:
      all_definitions.extend(settings.module_function_definitions)
  
  return all_definitions

def get_all_functions(settings=None) -> Dict[str, Callable]:
  """
  Get all available functions from both tools and modules.

  Args:
    settings: Optional settings object to check if modules are enabled

  Returns:
    Dict[str, Callable]: Dictionary of function names to function objects
  """
  all_functions = get_functions()
  
  # Add module functions if available
  if HAS_MODULE_SYSTEM and settings:
    # Access module_functions directly from settings if available
    if hasattr(settings, 'module_functions') and settings.module_functions:
      all_functions.update(settings.module_functions)
  
  return all_functions



##################################################
#              FUNCTION EXECUTION                #
##################################################
def execute_function(function_name: str, function_call: Dict[str, Any], settings=None) -> str:
  """
  Execute a function by name with the given parameters.

  Args:
    function_name: Name of the function to execute
    function_call: Dictionary containing function call details
    settings: Optional settings object to check if modules are enabled

  Returns:
    str: Result of the function call or error message
  """
  all_functions = get_all_functions(settings)
  
  if function_name in all_functions:
    try:
      # Call the function with parameters
      if "parameters" in function_call:
        return all_functions[function_name](**function_call["parameters"])
      else:
        return all_functions[function_name]()
    except Exception as e:
      return f"Error executing function {function_name}: {str(e)}"
  else:
    return f"Unknown function: {function_name}"

def process_function_calls(response: str, settings=None) -> str:
  """
  Process any function calls in the model response.
  Replaces each function call with its result, preserving the rest of the response.
  Supports multiple function calls in a single response.

  Args:
    response: The model response to process
    settings: Optional settings object to check if modules are enabled

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
    settings: Optional settings object to check if modules are enabled

  Returns:
    str: The function calling prompt
  """
  function_definitions_json = json.dumps(get_function_definitions(settings), indent=2)
  return FUNCTION_CALLING_PROMPT.format(
    function_definitions=function_definitions_json,
    function_format=FUNCTION_FORMAT
  )



# Export the functions
__all__ = [
  # Function discovery
  "get_function_definitions",
  "get_functions",
  "get_all_functions",

  # Function execution
  "execute_function",
  "process_function_calls",

  # Prompt generation
  "get_function_calling_prompt",

  # Tool functions
  "get_current_time",
  "get_current_date",
  "get_user_name",
  "greet_user"
]