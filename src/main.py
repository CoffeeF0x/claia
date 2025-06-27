#!/usr/bin/env python3
"""
Main entry point for the new src directory modules.
Allows user to select and run different modules.
"""

import importlib.util

# List of available modules
MODULES = [
    "agents",
    "cli",
    "commands",
    "common",
    "models",
    "modules",
    "tests"
]


def handle_module_selection(selected_module: str) -> None:
    """
    Handle the selected module by importing and running its __main__.py.

    Args:
        selected_module: The name of the selected module
    """
    print(f"Running module: {selected_module}")
    print("-" * 30)

    try:
        # Get the path to the module's __main__.py file
        module_main_path = f"src/{selected_module}/__main__.py"

        # Load and execute the __main__.py file
        spec = importlib.util.spec_from_file_location("__main__", module_main_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    except Exception as e:
        print(f"Error running module {selected_module}: {e}")

    print("-" * 30)


def display_menu() -> None:
    """Display the available modules menu."""
    print("\n" + "="*50)
    print("Available Modules:")
    print("="*50)

    for i, module in enumerate(MODULES, 1):
        print(f"{i}. {module}")

    print("0. Exit")
    print("="*50)


def get_user_selection() -> str:
    """
    Get user selection from the menu.

    Returns:
        The selected module name, or empty string to exit
    """
    while True:
        try:
            choice = input("\nEnter your choice (0-{}): ".format(len(MODULES)))

            if choice == "0":
                return ""

            choice_num = int(choice)
            if 1 <= choice_num <= len(MODULES):
                return MODULES[choice_num - 1]
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(MODULES)}.")

        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            return ""


def main() -> None:
    """Main function to run the module selector."""
    print("Welcome to the CLAIA Module Selector!")

    while True:
        display_menu()
        selected_module = get_user_selection()

        if not selected_module:
            print("Goodbye!")
            break

        handle_module_selection(selected_module)


if __name__ == "__main__":
    main()
