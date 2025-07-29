"""
Result demonstration functionality.
"""

from common.results import Result


class ResultDemo:
  """Demo class for Result functionality."""

  def __init__(self, session_dir: str):
    """Initialize with session directory."""
    self.session_dir = session_dir

  def run(self):
    """Demonstrate Result functionality."""
    print("\n=== Result Demo ===")
    print("Result provides standardized success/error handling.")

    try:
      # Success result
      success_result = Result.ok("Operation completed successfully!")
      print(f"✓ Success result: {success_result}")
      print(f"  - Is success: {success_result.is_success()}")
      print(f"  - Data: {success_result.get_data()}")

      # Error result
      error_result = Result.fail("Something went wrong", {"error_code": 404})
      print(f"✓ Error result: {error_result}")
      print(f"  - Is error: {error_result.is_error()}")
      print(f"  - Message: {error_result.get_message()}")
      print(f"  - Data: {error_result.get_data()}")

      # Shutdown result
      shutdown_result = Result.shutdown("Application is shutting down", exit_code=1)
      print(f"✓ Shutdown result: {shutdown_result}")
      print(f"  - Should exit: {shutdown_result.is_exit()}")
      print(f"  - Exit code: {shutdown_result.get_exit_code()}")

      # Custom result
      custom_result = Result(
        success=True,
        data={"processed": 100, "errors": 0},
        message="Batch processing completed"
      )
      print(f"✓ Custom result: {custom_result}")
      print(f"  - Data: {custom_result.get_data()}")

    except Exception as e:
      print(f"✗ Error in Result demo: {e}")
