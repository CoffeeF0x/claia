#!/usr/bin/env python3
"""
Test script to verify the new definitions plugin system.

This script tests the plugin-based model definitions to ensure
they are working correctly and can be discovered by the system.
"""

import sys
import os
import warnings

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.hooks.definition import definition_hooks
from models.definitions.legacy_definitions import LegacyDefinitionsPlugin
from models.definitions.openai_definitions import OpenAIDefinitionsPlugin
from models.definitions.anthropic_definitions import AnthropicDefinitionsPlugin


def test_legacy_definitions():
    """Test legacy definitions plugin."""
    print("Testing Legacy Definitions Plugin...")
    plugin = LegacyDefinitionsPlugin()
    definitions = plugin.get_model_definitions()

    print(f"Found {len(definitions)} legacy model definitions")
    for name, definition in definitions.items():
        print(f"  - {name}: {definition.title}")

    # Test specific models
    expected_models = ["gpt-4", "claude-3-5-sonnet", "minicpm3-4b"]
    for model_name in expected_models:
        if model_name in definitions:
            print(f"  ✓ {model_name} found")
        else:
            print(f"  ✗ {model_name} missing")

    return definitions


def test_openai_definitions():
    """Test OpenAI definitions plugin."""
    print("\nTesting OpenAI Definitions Plugin...")
    plugin = OpenAIDefinitionsPlugin()
    definitions = plugin.get_model_definitions()

    print(f"Found {len(definitions)} OpenAI model definitions")
    for name, definition in definitions.items():
        print(f"  - {name}: {definition.title}")

    # Test specific models
    expected_models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
    for model_name in expected_models:
        if model_name in definitions:
            print(f"  ✓ {model_name} found")
        else:
            print(f"  ✗ {model_name} missing")

    return definitions


def test_anthropic_definitions():
    """Test Anthropic definitions plugin."""
    print("\nTesting Anthropic Definitions Plugin...")
    plugin = AnthropicDefinitionsPlugin()
    definitions = plugin.get_model_definitions()

    print(f"Found {len(definitions)} Anthropic model definitions")
    for name, definition in definitions.items():
        print(f"  - {name}: {definition.title}")

    # Test specific models
    expected_models = ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    for model_name in expected_models:
        if model_name in definitions:
            print(f"  ✓ {model_name} found")
        else:
            print(f"  ✗ {model_name} missing")

    return definitions


def test_plugin_discovery():
    """Test plugin discovery via hook system."""
    print("\nTesting Plugin Discovery...")

    # Get all model definitions from the hook system
    all_definitions = {}

    # This would normally be done by the plugin manager
    plugins = [
        LegacyDefinitionsPlugin(),
        OpenAIDefinitionsPlugin(),
        AnthropicDefinitionsPlugin()
    ]

    for plugin in plugins:
        definitions = plugin.get_model_definitions()
        all_definitions.update(definitions)

    print(f"Total models discovered: {len(all_definitions)}")

    # Test some key models
    test_models = ["gpt-4", "claude-3-5-sonnet", "minicpm3-4b", "phi-4"]
    for model_name in test_models:
        if model_name in all_definitions:
            print(f"  ✓ {model_name} available")
        else:
            print(f"  ✗ {model_name} not available")

    return all_definitions


def test_deprecated_definitions():
    """Test that deprecated definitions.py still works but shows warnings."""
    print("\nTesting Deprecated Definitions...")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        try:
            from models.definitions import model_definitions
            print(f"Deprecated definitions loaded: {len(model_definitions)} models")
            print(f"Warning shown: {len(w) > 0}")
            if w:
                print(f"Warning message: {w[0].message}")
            return True
        except ImportError as e:
            print(f"Error loading deprecated definitions: {e}")
            return False


if __name__ == "__main__":
    print("=== Model Definitions Plugin System Test ===\n")

    # Test individual plugins
    legacy_defs = test_legacy_definitions()
    openai_defs = test_openai_definitions()
    anthropic_defs = test_anthropic_definitions()

    # Test plugin discovery
    all_defs = test_plugin_discovery()

    # Test deprecated compatibility
    test_deprecated_definitions()

    print("\n=== Test Complete ===")
    print(f"Total models across all plugins: {len(all_defs)}")

    # Summary
    print("\nSummary:")
    print(f"  Legacy definitions: {len(legacy_defs)} models")
    print(f"  OpenAI definitions: {len(openai_defs)} models")
    print(f"  Anthropic definitions: {len(anthropic_defs)} models")
    print(f"  Total unique models: {len(all_defs)} models")
