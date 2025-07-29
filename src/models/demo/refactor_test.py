"""
Test script for the refactored CLAIA models system.

This script demonstrates the new architecture:
registry -> solver -> deployment method -> model
"""

import logging
from models.registry import ModelRegistry
from common.files.conversation import Conversation



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               DEMO CLASS                             #
########################################################################
class RefactorTest:
  """Test the refactored models system."""

  def run(self):
    """Test the refactored models system."""
    logger.info("Testing refactored CLAIA models system")

    # Initialize registry (singleton)
    registry = ModelRegistry()

    # Test getting supported models
    logger.info("Getting supported models...")
    models = registry.get_supported_models()
    logger.info(f"Found {len(models)} supported models")
    for model in models[:5]:  # Show first 5
      logger.info(f"  - {model.name} ({model.title}) - {model.model_type}")

    # Test getting deployment methods
    logger.info("Getting deployment methods...")
    deployments = registry.get_supported_deployments()
    logger.info(f"Found {len(deployments)} deployment methods")
    for deployment in deployments:
      logger.info(f"  - {deployment.name} ({deployment.title})")

    # Test getting solvers
    logger.info("Getting solvers...")
    solvers = registry.get_supported_solvers()
    logger.info(f"Found {len(solvers)} solvers")
    for solver in solvers:
      logger.info(f"  - {solver.name} ({solver.title})")

    # Test model name resolution
    logger.info("Testing model name resolution...")
    test_names = ["gpt4", "claude", "gemma", "gpt-3.5-turbo"]
    for name in test_names:
      resolved = registry.resolve_model_name(name)
      logger.info(f"  '{name}' -> '{resolved}'")

    # Test cache stats
    logger.info("Cache stats:")
    stats = registry.get_cache_stats()
    logger.info(f"  Cached models: {stats['cached_models']}")
    logger.info(f"  Total memory: {stats['total_memory_mb']:.2f} MB")

    logger.info("Test completed successfully!")
