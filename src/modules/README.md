# CLAIA Modules System

The CLAIA Modules System allows for extending the application with custom commands and functions through external modules.

## How It Works

1. Modules are loaded from the directory specified in the `modules_directory` setting.
2. Each module must be in its own subdirectory and contain a `module.py` file.
3. The folder name becomes the command name for the module.
4. Modules can provide commands, functions, or both.
5. Commands are added to the application's command system and can be executed like built-in commands.
6. Functions are added to the application's function system and can be called by the application.

## Module Loading Process

The module loading process is as follows:

1. The application calls `modules.load(settings)` during startup.
2. The `load` function gets the modules directory from settings.
3. It iterates through each subdirectory in the modules directory.
4. For each subdirectory, it looks for a `module.py` file.
5. If found, it checks if the module has a `ModuleCommands` class and/or `FUNCTION_DEFINITIONS` list.
6. Module names are added to `settings.command_modules` and/or `settings.function_modules` lists for lazy loading.
7. Modules are only fully loaded when their commands or functions are actually needed.

## Lazy Loading

The module system uses lazy loading to improve performance:

1. During startup, only the names of modules are registered, not the actual module contents.
2. When a command is executed, the corresponding module is loaded on-demand.
3. When functions are needed, they are loaded from the modules on-demand.
4. This reduces memory usage and startup time, especially for applications with many modules.

## Creating a Module

To create a module:

1. Create a new directory in the modules directory (the directory name will be the command name).
2. Create a `module.py` file in the new directory.
3. Define your `ModuleCommands` class and/or functions in the `module.py` file.
4. Export your functions using the `FUNCTION_DEFINITIONS` list.

See the `sample_module` directory for an example module.

## Error Handling

The module system will:

1. Log errors if the modules directory is not defined or doesn't exist.
2. Skip modules that don't have a `module.py` file.
3. Log errors if a module fails to load.
4. Continue loading other modules even if some fail.

## Module Structure

A valid module must have the following structure:

```
modules/
  module_name/  # This becomes the command name
    module.py   # Required
    README.md   # Optional but recommended
    ...         # Other files as needed
```

The `module.py` file must contain one or both of the following:

- `ModuleCommands` class that inherits from `commands.base.Command`
- `FUNCTION_DEFINITIONS` list of function definition dictionaries

See the `sample_module` for a complete example of a module with both commands and functions. 