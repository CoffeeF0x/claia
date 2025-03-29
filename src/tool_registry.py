"""
Tool Registry for CLAIA

This module provides a central registry mapping tool names to their
corresponding implementation functions and handles their execution.
"""

# External dependencies
import logging
from typing import Dict, Callable, Any, Optional

# Internal dependencies
# Import the actual functions that implement the tools/commands.
# Adjust paths based on where command functions are defined.

# Add imports for real command functions when ready
# from commands.weather import get_weather_command
# from commands.calculator import calculate_command



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# For the demo, import from the examples directory
try:
    # This assumes src is in the Python path (e.g., added by conversation_demo.py)
    from examples.test_commands import echo_command, reverse_string_command
except ImportError:
    # Fallback or error handling if src isn't in the path during normal use
    logger.error("Could not import test commands. Ensure 'src' is in PYTHONPATH.")
    # Define dummy functions to prevent NameErrors if needed during development
    def echo_command(p, s): return "[ERROR: echo_command not loaded]"
    def reverse_string_command(p, s): return "[ERROR: reverse_string_command not loaded]"



########################################################################
#                             REGISTRY                                 #
########################################################################

# Define the type hint for a tool function
# Adjust based on the expected signature of your tool functions.
# This example assumes they take 'parameters' dict and optional 'settings'.
ToolFunction = Callable[[Dict[str, Any], Optional[Any]], str]

# The central registry mapping tool names (strings) to functions
TOOL_REGISTRY: Dict[str, ToolFunction] = {
    "echo": echo_command,
    "reverse_string": reverse_string_command,
    # Add other real tool names and functions here later
    # "get_weather": get_weather_command,
    # "calculate": calculate_command,
}



########################################################################
#                              EXECUTION                               #
########################################################################
def execute_tool(tool_name: str, parameters: Dict[str, Any], settings=None) -> str:
  """
  Executes a tool registered in the TOOL_REGISTRY.

  Args:
    tool_name: The name of the tool to execute.
    parameters: A dictionary of parameters for the tool function.
    settings: Optional settings object to pass to the tool function.

  Returns:
    The result of the tool execution as a string, or an error message string.
  """
  if tool_name not in TOOL_REGISTRY:
    error_msg = f"Error: Tool '{tool_name}' not found in registry."
    logger.error(error_msg)
    return error_msg

  tool_function = TOOL_REGISTRY[tool_name]

  try:
    # Execute the function with the provided parameters and settings
    # Ensure the function signature matches this call (takes parameters and settings)
    result = tool_function(parameters=parameters, settings=settings)
    # Convert result to string if it's not already
    return str(result)
  except Exception as e:
    error_msg = f"Error executing tool '{tool_name}': {str(e)}"
    logger.exception(f"Exception during execution of tool '{tool_name}' with params {parameters}") # Log with traceback
    return error_msg