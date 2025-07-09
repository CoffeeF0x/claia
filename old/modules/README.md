# CLAIA Modules System

This directory contains modules (plugins) that extend the functionality of CLAIA.

## Creating a New Module

Creating a new module is simple:

1. Create a new directory in the `modules` folder with your module name (e.g., `modules/mymodule/`)
2. Add a `command.py` file to your module directory
3. In `command.py`, create a class that inherits from `Command` and define your commands

### Module Structure

A basic module should have this structure:

```
modules/
  mymodule/           # Your module directory
    command.py        # Command implementation
    README.md         # (Optional) Documentation for your module
```

### Example Module

Here's a minimal example of a `command.py` file:

```python
from commands.base import Command, command
from settings import Settings
from results import Result

class MyModuleCommand(Command):
    """My custom module command class."""

    @command(
        path=["hello"],
        description="Say hello",
        parameters={
            "type": "object",
            "properties": {}
        },
        ai_callable=True
    )
    def hello_command(self, settings: Settings) -> Result:
        """Simple hello command."""
        result = Result()
        result.message = "Hello from my module!"
        return result
```

### How It Works

When CLAIA starts:

1. The module loader looks for directories in the `modules` folder
2. For each directory, it checks for a `command.py` file
3. If found, it imports the file and looks for a class that inherits from `Command`
4. It creates an instance of that class and registers its commands with the system
5. Commands are accessible through both the CLI and AI interfaces using the module name prefix

### Command Naming

Commands are registered with a prefix based on the module name:

- If your module is called `mymodule` and has a command `hello`, it will be registered as `modules_mymodule_hello` in the command registry
- In the CLI, you can access it as `mymodule hello`
- AI functions can call it using the full name `modules_mymodule_hello`

### Best Practices

1. **Keep it Simple**: Modules should be focused on a specific task or domain
2. **Consistent Returns**: Always return a `Result` object from your commands
3. **Good Documentation**: Include a README.md that explains your module's purpose and commands
4. **Descriptive Commands**: Use clear command names and descriptions
5. **Error Handling**: Handle errors gracefully and provide helpful error messages in Results
