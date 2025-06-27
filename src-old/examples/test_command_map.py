#!/usr/bin/env python3
"""
Test script for the new command map structure

This script demonstrates how the new command system works with
the flat dictionary map instead of the hierarchical tree structure.
"""

# External dependencies
import logging
import sys
import os

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)



########################################################################
#                           TEST FRAMEWORK                             #
########################################################################
def test_registry():
    """Test the Registry and command map structure"""

    # Ensure test is run from the project root directory
    if os.path.basename(os.getcwd()) == 'src':
        os.chdir('..')

    # Add the src directory to the Python path
    sys.path.insert(0, "src")

    # Import the Registry, Settings, and tools one by one to avoid circular imports
    from settings import Settings

    # Create a Settings instance
    settings = Settings()

    # Import Registry after settings to avoid circular imports
    from commands import Registry
    registry = Registry()

    # Print summary of commands in the registry
    logger.info(f"Registry contains {len(registry.command_map)} commands")

    # Create a test function to execute commands
    def run_command(command_str):
        print(f"\n> {command_str}")
        result = registry.run(command_str, settings)
        if result and hasattr(result, 'message') and callable(getattr(result, 'message')):
            print(result.message())
        return result

    # Print commands in each module
    print("\nCommands by module:")
    modules = {}
    for cmd_name in registry.command_map:
        if not cmd_name.startswith("cli_"):
            parts = cmd_name.split("_")
            if len(parts) > 0:
                module_name = parts[0]
                if module_name not in modules:
                    modules[module_name] = []
                modules[module_name].append(cmd_name)

    for module_name, commands in sorted(modules.items()):
        print(f"\n{module_name.capitalize()} module ({len(commands)} commands):")
        # Print a sample of commands (first 5)
        for cmd in sorted(commands)[:5]:
            print(f"  - {cmd}")
        if len(commands) > 5:
            print(f"  - ... ({len(commands) - 5} more)")

    # Test some CLI commands
    print("\nTesting CLI commands:")
    run_command("system get log-level")
    run_command("system get log-format")

    # Test the new simplified commands
    print("\nTesting new simplified commands:")
    run_command("system get setting=log-level")
    run_command("system set setting=log-level value=debug")
    run_command("system get setting=log-level")

    # Test direct function execution via registry
    print("\nTesting direct function execution via registry:")
    result = registry.execute_tool("system_get", {"setting": "log-level"}, settings)
    print(f"system_get result: {result}")

    result = registry.execute_tool("system_set", {"setting": "log-level", "value": "info"}, settings)
    print(f"system_set result: {result}")

    result = registry.execute_tool("system_get", {"setting": "log-level"}, settings)
    print(f"system_get result: {result}")

    # Print some AI function definitions
    print("\nAI Function definitions sample:")
    function_defs = registry.get_tool_definitions()
    print(f"Total AI-callable functions: {len(function_defs)}")

    # Print first 3 function definitions (if available)
    for i, func_def in enumerate(function_defs[:min(3, len(function_defs))]):
        print(f"\nFunction {i+1}:")
        print(f"  Name: {func_def['name']}")
        print(f"  Description: {func_def['description']}")



########################################################################
#                                MAIN                                  #
########################################################################
if __name__ == "__main__":
    print("Testing new command map structure")
    try:
        test_registry()
        print("\nTest complete!")
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()