#!/usr/bin/env python3
"""Simple test for definitions plugin system."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Test individual plugins
    from models.definitions.legacy_definitions import LegacyDefinitionsPlugin
    from models.definitions.openai_definitions import OpenAIDefinitionsPlugin
    from models.definitions.anthropic_definitions import AnthropicDefinitionsPlugin

    legacy = LegacyDefinitionsPlugin()
    openai = OpenAIDefinitionsPlugin()
    anthropic = AnthropicDefinitionsPlugin()

    legacy_defs = legacy.get_model_definitions()
    openai_defs = openai.get_model_definitions()
    anthropic_defs = anthropic.get_model_definitions()

    print(f"Legacy: {len(legacy_defs)} models")
    print(f"OpenAI: {len(openai_defs)} models")
    print(f"Anthropic: {len(anthropic_defs)} models")

    # Test deprecated import
    import warnings
    with warnings.catch_warnings(record=True) as w:
        from models.definitions import model_definitions
        print(f"Deprecated: {len(model_definitions)} models")
        if w:
            print(f"Warning: {w[0].message}")

    print("✓ All tests passed")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
