#!/usr/bin/env python3
"""
Test script for invalid command handling

This script tests what happens when invalid commands are entered
to make sure the system shows helpful information.
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
def test_invalid_commands():
    """Test how the system handles invalid commands"""

    # Ensure test is run from the project root directory
    if os.path.basename(os.getcwd()) == 'src':
        os.chdir('..')

    # Add the src directory to the Python path
    sys.path.insert(0, "src")

    # Import Registry and Settings
    from settings import Settings
    from commands import Registry

    # Create instances
    settings = Settings()
    registry = Registry()

    # Helper function to run a command and capture the output
    def run_command(command_str):
        print(f"\n> {command_str}")
        old_stdout = sys.stdout
        try:
            from io import StringIO
            captured_output = StringIO()
            sys.stdout = captured_output
            result = registry.run(command_str, settings)
            sys.stdout = old_stdout
            output = captured_output.getvalue()
            print(output)
            return result, output
        except Exception as e:
            sys.stdout = old_stdout
            print(f"ERROR: {e}")
            return None, None

    # Test invalid top-level command
    print("\nTesting invalid top-level command:")
    run_command("foobar")

    # Test invalid module command
    print("\nTesting invalid module command:")
    run_command("system foobar")

    # Test incomplete module command
    print("\nTesting incomplete module command:")
    run_command("system")

    # Test another module with invalid command
    print("\nTesting another module with invalid command:")
    run_command("model foobar")

    print("\nTesting module help command:")
    run_command("help system")



########################################################################
#                                MAIN                                  #
########################################################################
if __name__ == "__main__":
    print("Testing invalid command handling")
    try:
        test_invalid_commands()
        print("\nTest complete!")
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()