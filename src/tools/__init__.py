"""
Tools module for Claia

This module provides function calling capabilities for AI models.
It includes the function calling prompt and tools that can be called by the AI.
"""

import json
import importlib
from typing import Dict, Any, List, Callable, Optional, Tuple

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

When you need to call a function, use the following format:
{function_format}

Incorporate the function call into the response where necessary.
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

def process_function_calls(response: str, settings=None) -> Tuple[str, Optional[str]]:
  """
  Process any function calls in the model response.

  Args:
    response: The model response to process
    settings: Optional settings object to check if modules are enabled

  Returns:
    Tuple[str, Optional[str]]: A tuple containing (final_response, raw_function_call)
      - final_response: The processed response (either the function result or the original response)
      - raw_function_call: The raw function call string if a function was called, None otherwise
  """
  if not response or "[FUNCTION_CALL]" not in response:
    return response, None

  try:
    start = response.index("[FUNCTION_CALL]") + len("[FUNCTION_CALL]")
    end = response.index("[/FUNCTION_CALL]")
    function_call_str = response[start:end]
    function_call = json.loads(function_call_str)
    function_name = function_call["name"]

    # Execute the function
    result = execute_function(function_name, function_call, settings)

    # Return the result and the raw function call
    return result, response[response.index("[FUNCTION_CALL]"):end + len("[/FUNCTION_CALL]")]
  except Exception as e:
    # If there's an error processing the function call, return the original response
    return f"Error processing function call: {str(e)}", None



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