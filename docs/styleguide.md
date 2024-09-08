# Programming Style Guide

## General Principles (Applicable to All Languages)

1. **Consistency**: Follow the style guide consistently throughout the project.

2. **Readability**: Write code that is easy to read and understand.

3. **Simplicity**: Keep code simple and avoid unnecessary complexity.

4. **Documentation**: Write clear and concise documentation for your code.

5. **DRY (Don't Repeat Yourself)**: Avoid code duplication.

6. **SOLID Principles**: Follow SOLID principles for object-oriented design.

7. **Testing**: Write unit tests for your code.

8. **Version Control**: Use meaningful commit messages and follow Git best practices.

9. **Error Handling**: Implement proper error handling and logging.

10. **Security**: Follow security best practices and avoid common vulnerabilities.

11. **Performance**: Write efficient code, but prioritize readability unless performance is critical.

12. **Naming Conventions**:

    - Use descriptive and meaningful names for variables, functions, and classes.
    - Avoid abbreviations unless they are widely understood.

13. **Comments**:

    - Write meaningful comments explaining "why", not "what".
    - Keep comments up-to-date with the code.

14. **File Organization**:

    - Group related code together.
    - Separate interface from implementation when applicable.

15. **Code Formatting**:

    - Use consistent indentation.
    - Limit line length for better readability.
    - Use blank lines to separate logical sections of code.

16. **Resource Management**:

    - Properly manage resources (memory, file handles, etc.).
    - Use appropriate patterns or language features for resource cleanup.

## Python Style Guide

Based on [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications.

### 1. Indentation and Whitespace

- Use 2 spaces per indentation level.
- Never use tabs for indentation.
- Avoid extraneous whitespace in the following situations:
  - Immediately inside parentheses, brackets, or braces.
  - Between a trailing comma and a closing parenthesis.
  - Immediately before a comma, semicolon, or colon.
- Surround binary operators with a single space on either side.
- Use blank lines to separate functions and classes, and larger blocks of code inside functions.

### 2. Maximum Line Length

- Limit all lines to a maximum of 79 characters for code.
- For comments and docstrings, limit lines to 72 characters.

### 3. Imports

- Import statements should be on separate lines.
- Imports should be grouped in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports
- Use absolute imports when possible.
- Avoid wildcard imports (from module import *).

### 4. Naming Conventions

- Functions, variables, and attributes: lowercase_with_underscores
- Classes and Exceptions: CapitalizedWords
- Constants: ALL_CAPS_WITH_UNDERSCORES
- Protected instance attributes: _leading_underscore
- Private instance attributes: __double_leading_underscore

### 5. Functions and Methods

- Use def statements to create functions.
- Use type hints for function arguments and return values.
- Use docstrings to describe the function's purpose and parameters.

### 6. Classes

- Use class statements to create classes.
- Use CamelCase for class names.
- Use self for the first argument to instance methods.
- Use cls for the first argument to class methods.

### 7. String Formatting

- Prefer f-strings for string formatting when possible.
- Use .format() method as a second choice.
- Avoid using % operator for string formatting.

### 8. Error Handling

- Use try/except blocks to handle exceptions.
- Be specific about the exceptions you're catching.
- Use context managers (with statements) when dealing with resources.

### 9. Type Checking

- Use isinstance() for type checking, not type().

### 10. File and Directory Paths

- Use pathlib for file and directory path manipulations.

## C++ Style Guide

Based on the [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html) with some modifications.

### 1. Naming Conventions

- Use snake_case for function and variable names
- Use PascalCase for class and struct names
- Use UPPER_CASE for constants and macros
- Use m_ prefix for class member variables

### 2. Indentation and Formatting

- Use 2 spaces for indentation
- Never use tabs for indentation
- Place opening braces on the same line as the statement
- Put closing braces on a new line
- Use spaces around operators and after commas

### 3. File Organization

- Use .hpp for header files and .cpp for source files
- Use #pragma once for header guards
- Order includes as follows:
  1. Related header
  2. C system headers
  3. C++ standard library headers
  4. Other libraries' headers
  5. Your project's headers

### 4. Classes and Structs

- Declare public members first, then protected, then private
- Use explicit constructors when appropriate
- Declare destructors virtual in base classes
- Follow the Rule of Three/Five/Zero

### 5. Functions

- Keep functions short and focused on a single task
- Use const for parameters that aren't modified
- Use references for non-pointer parameters
- Use nullptr instead of NULL

### 6. Variables

- Initialize variables at declaration when possible
- Use const whenever appropriate
- Avoid global variables

### 7. Memory Management

- Prefer smart pointers (std::unique_ptr, std::shared_ptr) over raw pointers
- Use RAII (Resource Acquisition Is Initialization) principle

### 8. Modern C++ Features

- Use auto for type inference when appropriate
- Use range-based for loops when possible
- Use nullptr instead of NULL
- Use constexpr for compile-time constants
- Use override for virtual function overrides

### 9. Templates

- Keep template code in header files
- Use concepts (C++20) to constrain template parameters

### 10. Namespaces

- Use namespaces to avoid naming conflicts
- Don't use using namespace in header files

### 11. Casting

- Use static_cast, dynamic_cast, const_cast, and reinterpret_cast instead of C-style casts

### 12. File and Console I/O

- Prefer C++ streams (iostream) over C-style I/O (stdio.h)

### 13. Preprocessor Directives

- Minimize use of #define, prefer const or constexpr
- Use #ifdef, #ifndef for conditional compilation

### 14. Lambda Expressions

- Use lambda expressions for short, one-off functions

## JavaScript Style Guide (with Vue.js focus)

Based on [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) and [Vue.js Style Guide](https://vuejs.org/style-guide/) with some modifications.

### 1. Indentation and Formatting

- Use 2 spaces for indentation.
- Never use tabs for indentation.
- Use semicolons at the end of statements.
- Use single quotes for strings.
- Place opening braces on the same line as the statement.
- Add spaces inside curly braces for object literals.

### 2. Naming Conventions

- Use camelCase for variables and functions.
- Use PascalCase for classes and Vue components.
- Use UPPER_CASE for constants.
- Prefix private properties and methods with an underscore.

### 3. Variables

- Use `const` for all of your references; avoid using `var`.
- If you must reassign references, use `let` instead of `var`.
- Use meaningful and pronounceable variable names.

### 4. Functions

- Use arrow functions where possible.
- Keep functions small and focused on a single task.
- Use default parameters instead of mutating function arguments.

### 5. Classes & Constructors

- Use `class` syntax.
- Use `extends` for inheritance.
- Methods can return `this` to help with method chaining.

### 6. Modules

- Always use modules (`import`/`export`) over a non-standard module system.
- Do not use wildcard imports.

### 7. Vue.js Specific

- Use multi-word component names to avoid conflicts with existing and future HTML elements.
- Use PascalCase for component names in single-file components and string templates.
- Use kebab-case for component names in DOM templates.
- Order component options consistently (e.g., data, computed, methods, lifecycle hooks).
- Use `v-for` with a `key` attribute.
- Avoid `v-if` with `v-for`.
- Use component-scoped styling with `scoped` attribute.

### 8. Props

- Use camelCase in JavaScript and kebab-case in HTML.
- Validate props using definitions.
- Use verbose prop definitions (objects instead of arrays).

### 9. Vuex (if used)

- Use separate files for state, getters, actions, and mutations.
- Use constants for mutation types.

### 10. Testing

- Write unit tests for components and Vuex stores.
- Use Vue Test Utils for component testing.

### 11. Error Handling

- Use `try-catch` blocks for synchronous code.
- Use `.catch()` for promises.

### 12. Comments

- Use `//` for single line comments.
- Use `/** ... */` for multi-line comments.
- Start all comments with a space.

### 13. Whitespace

- Use blank lines to separate groups of related statements.
- Do not use multiple blank lines.

### 14. Commas

- Use trailing commas for multi-line object literals.

### 15. Semicolons

- Use semicolons at the end of statements.

### 16. Type Checking

- Use `typeof` for primitive types.
- Use `instanceof` for objects.

### 17. Conditional Statements

- Use `===` and `!==` over `==` and `!=`.
- Use shortcuts for booleans, but explicit comparisons for strings and numbers.

### 18. Blocks

- Use braces with all multi-line blocks.
- If you're using multi-line blocks with `if` and `else`, put `else` on the same line as your `if` block's closing brace.
