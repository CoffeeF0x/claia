#!/usr/bin/env python3
"""
Test runner for CLAIA.
"""

# External dependencies
import os
import sys
import importlib
import logging
from typing import List

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))



########################################################################
#                            INITIALIZATION                            #
########################################################################
# Set up logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def discover_tests() -> List[str]:
  """
  Discover all test modules in the tests directory.

  Returns:
      List[str]: A list of test module names
  """
  tests_dir = os.path.dirname(__file__)
  test_modules = []

  for filename in os.listdir(tests_dir):
    if filename.startswith('test_') and filename.endswith('.py'):
      module_name = filename[:-3]  # Remove .py extension
      test_modules.append(module_name)

  return test_modules


def run_test(module_name: str) -> bool:
  """
  Run a test module.

  Args:
      module_name: The name of the test module to run

  Returns:
      bool: True if the test passed, False otherwise
  """
  try:
    logger.info(f"Running test: {module_name}")
    module = importlib.import_module(module_name)

    # Look for a test_* function in the module
    test_functions = [
      func for func in dir(module)
      if callable(getattr(module, func)) and func.startswith('test_')
    ]

    if not test_functions:
      logger.warning(f"No test functions found in {module_name}")
      return False

    # Run each test function
    for func_name in test_functions:
      logger.info(f"Running test function: {func_name}")
      test_func = getattr(module, func_name)
      test_func()

    logger.info(f"Test {module_name} completed successfully")
    return True
  except Exception as e:
    logger.error(f"Test {module_name} failed: {e}")
    return False



########################################################################
#                             MAIN FUNCTION                            #
########################################################################
def main():
  """
  Main function to run all tests.
  """
  test_modules = discover_tests()

  if not test_modules:
    logger.warning("No test modules found")
    return

  logger.info(f"Found {len(test_modules)} test modules: {', '.join(test_modules)}")

  # Run all tests
  results = []
  for module_name in test_modules:
    result = run_test(module_name)
    results.append((module_name, result))

  # Print summary
  logger.info("Test Summary:")
  passed = sum(1 for _, result in results if result)
  failed = len(results) - passed

  for module_name, result in results:
    status = "PASSED" if result else "FAILED"
    logger.info(f"  {module_name}: {status}")

  logger.info(f"Total: {len(results)}, Passed: {passed}, Failed: {failed}")

  # Exit with non-zero code if any tests failed
  if failed > 0:
    sys.exit(1)


if __name__ == "__main__":
  main()