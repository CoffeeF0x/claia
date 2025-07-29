#!/usr/bin/env python3
"""
Test script for the dynamic plugin system.
This script verifies that plugins can be loaded and used correctly.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_plugin_loading():
  """Test that plugins can be loaded dynamically."""
  print("="*60)
  print("TESTING DYNAMIC PLUGIN SYSTEM")
  print("="*60)

  try:
    from models.manager import ModuleManager

    # Create manager and load plugins
    print("\n1. Creating ModuleManager...")
    manager = ModuleManager()

    print("\n2. Loading plugins...")
    manager.load_all_plugins()

    # Test model plugins
    print("\n3. Testing model plugins...")
    supported_models = manager.get_supported_models()
    print(f"   Found {len(supported_models)} supported models:")
    for model_name, model_info in supported_models.items():
      print(f"   - {model_name}: {model_info.title} ({model_info.provider})")

    # Test deployment plugins
    print("\n4. Testing deployment plugins...")
    deployment_info = manager.get_available_deployments()
    print(f"   Found {len(deployment_info)} deployment methods:")
    for deploy_name, deploy_info in deployment_info.items():
      print(f"   - {deploy_name}: {deploy_info.title}")

    # Test solver plugins
    print("\n5. Testing solver plugins...")
    solver_info = manager.get_available_solvers()
    print(f"   Found {len(solver_info)} solvers:")
    for solver_name, info in solver_info.items():
      print(f"   - {solver_name}: {info.title} (priority: {info.priority})")

    # Test getting best solver
    print("\n6. Testing solver selection...")
    best_solver = manager.get_solver_plugin()
    if best_solver:
      solver_info = best_solver.get_solver_info()
      print(f"   Best solver: {solver_info.name} - {solver_info.title}")
    else:
      print("   No solver found!")
      return False

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED! Plugin system is working correctly.")
    print("="*60)
    return True

  except Exception as e:
    print(f"\n❌ TEST FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    return False

def test_entry_points():
  """Test entry point discovery."""
  print("\n" + "="*60)
  print("TESTING ENTRY POINT DISCOVERY")
  print("="*60)

  try:
    import importlib.metadata as metadata

    # Test model entry points
    print("\n1. Checking model entry points...")
    model_entries = list(metadata.entry_points().select(group='claia.models'))
    print(f"   Found {len(model_entries)} model entry points:")
    for entry in model_entries:
      print(f"   - {entry.name}: {entry.value}")

    # Test deployment entry points
    print("\n2. Checking deployment entry points...")
    deploy_entries = list(metadata.entry_points().select(group='claia.deployments'))
    print(f"   Found {len(deploy_entries)} deployment entry points:")
    for entry in deploy_entries:
      print(f"   - {entry.name}: {entry.value}")

    # Test solver entry points
    print("\n3. Checking solver entry points...")
    solver_entries = list(metadata.entry_points().select(group='claia.solvers'))
    print(f"   Found {len(solver_entries)} solver entry points:")
    for entry in solver_entries:
      print(f"   - {entry.name}: {entry.value}")

    if model_entries or deploy_entries or solver_entries:
      print("\n✅ Entry points found! Dynamic discovery should work.")
    else:
      print("\n⚠️  No entry points found. Will fall back to built-in plugins.")

    return True

  except Exception as e:
    print(f"\n❌ Entry point test failed: {str(e)}")
    return False

def main():
  """Run all tests."""
  print("CLAIA Plugin System Test")
  print("This tests the dynamic plugin loading system.")

  # Test entry point discovery
  entry_test_passed = test_entry_points()

  # Test plugin loading
  plugin_test_passed = test_plugin_loading()

  if entry_test_passed and plugin_test_passed:
    print("\n🎉 All tests passed! The plugin system is ready for external plugins.")
    return 0
  else:
    print("\n💥 Some tests failed. Check the errors above.")
    return 1

if __name__ == "__main__":
  exit(main())
