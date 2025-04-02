#!/usr/bin/env python3
"""
Test script for module command execution.

This script demonstrates how to execute module commands programmatically.
It can be used as a reference for implementing direct command execution in main.py.
"""

import os
import sys
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Add paths for imports
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import required modules
from commands import Registry
from settings import Settings
from mod import load_modules
from results import Result



########################################################################
#                               HELPERS                                #
########################################################################
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test module commands')
    parser.add_argument('command', nargs='*', help='Command to execute')
    return parser.parse_args()


def parse_command_string(command_str):
    """Parse a command string into module, command and parameters."""
    parts = command_str.split()

    if len(parts) < 2:
        logger.error("Command format should be: module_name command_name [params]")
        return None, None, {}

    module_name = parts[0]
    command_name = parts[1]

    # Parse parameters (key=value format)
    params = {}
    for i in range(2, len(parts)):
        part = parts[i]
        if "=" in part:
            key, value = part.split("=", 1)
            # Note: Quotes have already been processed by the shell
            # so we don't need to handle them explicitly here
            params[key] = value

    return module_name, command_name, params



########################################################################
#                                MAIN                                  #
########################################################################
def main():
    """Run the test script."""
    # Parse command line arguments
    args = parse_args()

    # Initialize settings and registry
    settings = Settings()
    registry = Registry()

    # Get modules directory
    modules_dir = os.path.join(os.path.dirname(src_dir), "modules")

    # Load modules
    loaded_modules = load_modules(registry, modules_dir)

    if not args.command:
        # If no command provided, print available module commands
        print("Available module commands:")
        for module_name, module_instance in loaded_modules.items():
            print(f"\nModule: {module_name}")
            if hasattr(module_instance, 'command_map'):
                for cmd_name in module_instance.command_map.keys():
                    print(f"  - {cmd_name}")
        return

    # Join the command arguments into a string
    command_str = ' '.join(args.command)
    logger.info(f"Executing command: {command_str}")

    # Parse the command string
    module_name, command_name, params = parse_command_string(command_str)

    if not module_name or not command_name:
        return

    # Build the full command name with module prefix
    full_command = f"modules_{module_name}_{command_name}"

    # Check if the command exists
    if full_command in registry.command_map:
        logger.info(f"Executing module command: {full_command}")

        # Execute the command
        result = registry.execute_tool(full_command, params, settings)

        # Print the result
        if isinstance(result, Result):
            print(result.message)
        else:
            print(result)
    else:
        logger.error(f"Command not found: {full_command}")

        # Print similar commands to help the user
        print("\nSimilar commands:")
        for cmd_name in registry.command_map.keys():
            if cmd_name.startswith(f"modules_{module_name}_"):
                print(f"  - {cmd_name}")



if __name__ == "__main__":
    main()