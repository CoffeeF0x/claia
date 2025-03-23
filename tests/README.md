# Test Structure

This directory contains all tests for the project. The test structure mirrors the source code structure to make it easy to find and maintain tests.

## Directory Structure

```
tests/
├── conftest.py              # Shared pytest fixtures and configuration
├── test_data/              # Test data files and resources
└── conversations/          # Tests for conversation-related functionality
    ├── test_conversation.py
    └── test_message.py
```

## Running Tests

To run all tests:
```bash
pytest
```

To run tests with coverage:
```bash
pytest --cov=src
```

To run a specific test file:
```bash
pytest tests/conversations/test_conversation.py
```

## Writing Tests

1. Follow the existing directory structure
2. Name test files with `test_` prefix
3. Name test functions with `test_` prefix
4. Use fixtures from conftest.py when possible
5. Add docstrings to test functions
6. Group tests logically using classes if needed