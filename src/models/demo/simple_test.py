"""
Simple test for the simplified CLAIA models architecture.

Tests the new flow: registry -> solver (with name resolution) -> deployment
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import ModelRegistry
from common.files.conversation import Conversation, Message

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simplified_architecture():
  """Test the simplified models architecture."""
  print("=== Testing Simplified CLAIA Models Architecture ===")

  try:
    # Initialize registry
    print("\n1. Initializing ModelRegistry...")
    registry = ModelRegistry()

    # Test getting supported models
    print("\n2. Getting supported models...")
    models = registry.get_supported_models()
    print(f"Found {len(models)} supported models:")
    for name, info in list(models.items())[:3]:  # Show first 3
      print(f"  - {name}: {info.title}")

    # Test getting deployment methods
    print("\n3. Getting deployment methods...")
    deployments = registry.get_available_deployments()
    print(f"Found {len(deployments)} deployment methods:")
    for name, info in deployments.items():
      print(f"  - {name}: {info.title}")

    # Test getting solvers
    print("\n4. Getting solvers...")
    solvers = registry.get_available_solvers()
    print(f"Found {len(solvers)} solvers:")
    for name, info in solvers.items():
      print(f"  - {name}: {info.title}")

    # Test solver directly (without actual model run)
    print("\n5. Testing solver logic...")
    if models and deployments:
      model_name = list(models.keys())[0]  # Use first available model
      available_deployments = list(deployments.keys())

      # Get solver
      solver = registry.manager.get_solver_plugin()
      if solver:
        print(f"Testing with model '{model_name}' and deployments {available_deployments}")

        # Test solver
        result = solver.solve_deployment(
          model_name=model_name,
          available_deployments=available_deployments,
          available_models=models
        )

        if result.is_success():
          params = result.data
          print(f"✓ Solver result: deployment='{params.deployment_name}', model='{params.model_name}'")
        else:
          print(f"✗ Solver failed: {result.error_message}")
      else:
        print("✗ No solver available")

    print("\n6. Testing cache stats...")
    stats = registry.get_cache_stats()
    print(f"Cache stats: {stats}")

    print("\n=== Test completed successfully! ===")

  except Exception as e:
    print(f"\n✗ Test failed with error: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
  test_simplified_architecture()
