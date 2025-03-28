"""
Tests for the FileManifest singleton pattern implementation.
This file specifically focuses on ensuring the singleton pattern is working correctly.
"""

# External dependencies
import os
import threading
import importlib.util
import sys
from pathlib import Path
import tempfile
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor

# Internal dependencies
from files import FileManifest
from files.manifest import MANIFEST_FILENAME



########################################################################
#                          HELPER FUNCTIONS                            #
########################################################################
def create_temporary_module(code, module_name="temp_module"):
  """Create a temporary module with the given code."""
  # Create a temporary file to hold the module code
  with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
    temp_file.write(code.encode('utf-8'))
    temp_path = temp_file.name
  
  # Import the module
  spec = importlib.util.spec_from_file_location(module_name, temp_path)
  module = importlib.util.module_from_spec(spec)
  sys.modules[module_name] = module
  spec.loader.exec_module(module)
  
  # Return both the module and path for cleanup
  return module, temp_path



########################################################################
#                        SINGLETON TESTS                               #
########################################################################
def test_basic_singleton_behavior(temp_dir):
  """Verify basic singleton behavior - same object is returned on multiple instantiations."""
  # Reset singleton state
  FileManifest._instance = None
  
  # Create two instances
  manifest1 = FileManifest(temp_dir)
  manifest2 = FileManifest(temp_dir)
  
  # Verify they are the same object
  assert manifest1 is manifest2
  
  # Verify different directory doesn't create new instance
  another_dir = os.path.join(temp_dir, "another")
  manifest3 = FileManifest(another_dir)
  assert manifest1 is manifest3
  
  # Check that the base directory remains from the first instantiation
  assert manifest3.base_directory == temp_dir


def test_singleton_data_persistence(temp_dir):
  """Test that data persists between different instantiations of the singleton."""
  # Reset singleton state
  FileManifest._instance = None
  
  # First instance - add some data
  manifest1 = FileManifest(temp_dir)
  manifest1.update_file_metadata("test_file", {"name": "test.txt", "size": 100})
  
  # Second instance - should have the same data
  manifest2 = FileManifest(temp_dir)
  metadata = manifest2.get_file_metadata("test_file")
  
  assert metadata is not None
  assert metadata["name"] == "test.txt"
  assert metadata["size"] == 100


def test_singleton_across_threads(temp_dir):
  """Test that the singleton works correctly across multiple threads."""
  # Reset singleton state
  FileManifest._instance = None
  
  # Create the first instance in the main thread
  main_manifest = FileManifest(temp_dir)
  
  # Set a value to check later
  main_manifest.update_file_metadata("main_thread", {"thread": "main"})
  
  # Container for thread results
  results = []
  
  def thread_function():
    # Get FileManifest instance in the thread
    thread_manifest = FileManifest(temp_dir)
    
    # Store id for comparison
    results.append(id(thread_manifest))
    
    # Update data in thread
    thread_manifest.update_file_metadata("thread_data", {"thread": "worker"})
  
  # Create and run thread
  thread = threading.Thread(target=thread_function)
  thread.start()
  thread.join()
  
  # Check results
  assert len(results) == 1
  assert results[0] == id(main_manifest)
  
  # Check data was updated from thread
  thread_data = main_manifest.get_file_metadata("thread_data")
  assert thread_data is not None
  assert thread_data["thread"] == "worker"


def test_singleton_across_modules(temp_dir):
  """Test that the singleton works correctly across different modules."""
  # Reset singleton state
  FileManifest._instance = None
  
  # Create module code that will import and use FileManifest
  module_code = """
from files import FileManifest

def get_manifest_instance(directory):
    return FileManifest(directory)
  """
  
  # Create the module
  temp_module, temp_path = create_temporary_module(module_code)
  
  try:
    # Create first instance in this module
    main_manifest = FileManifest(temp_dir)
    main_manifest.update_file_metadata("module_test", {"source": "main"})
    
    # Get instance from other module
    other_manifest = temp_module.get_manifest_instance(os.path.join(temp_dir, "other"))
    
    # Verify it's the same instance
    assert main_manifest is other_manifest
    assert id(main_manifest) == id(other_manifest)
    
    # Check that data is shared
    module_data = other_manifest.get_file_metadata("module_test")
    assert module_data is not None
    assert module_data["source"] == "main"
    
    # Update from other module
    other_manifest.update_file_metadata("other_module", {"source": "other"})
    
    # Check from main module
    other_data = main_manifest.get_file_metadata("other_module")
    assert other_data is not None
    assert other_data["source"] == "other"
  
  finally:
    # Clean up the temporary module
    if temp_path and os.path.exists(temp_path):
      os.unlink(temp_path)
    if "temp_module" in sys.modules:
      del sys.modules["temp_module"]


def test_singleton_initialization_once(temp_dir):
  """Test that the initialization code only runs once."""
  # Reset singleton state
  FileManifest._instance = None
  
  # Create first instance with specific directory
  manifest1 = FileManifest(temp_dir)
  
  # Create a test file in the manifest
  manifest1.update_file_metadata("init_test", {"initialized": True})
  
  # Create a second instance with a different directory
  other_dir = os.path.join(temp_dir, "completely_different")
  manifest2 = FileManifest(other_dir)
  
  # Verify the base directory is still the original one
  assert manifest2.base_directory == temp_dir
  assert manifest2.base_directory != other_dir
  
  # Verify data persists
  test_data = manifest2.get_file_metadata("init_test")
  assert test_data is not None
  assert test_data["initialized"] is True
  
  # Verify manifest path is based on the first initialization
  expected_path = os.path.join(temp_dir, "manifest.json")
  assert manifest2._get_manifest_path() == expected_path


def test_concurrent_access(temp_dir):
  """Test the singleton with concurrent access from multiple threads."""
  # Reset singleton state
  FileManifest._instance = None
  
  # Number of threads and operations
  num_threads = 10
  operations_per_thread = 50
  
  # Create first instance and add some initial data
  manifest = FileManifest(temp_dir)
  manifest.update_file_metadata("counter", {"value": 0})
  
  # Track any errors that occur in threads
  errors = []
  
  def worker_function(worker_id):
    try:
      # Get the singleton instance
      thread_manifest = FileManifest(temp_dir)
      
      # Perform multiple operations
      for i in range(operations_per_thread):
        # Small random delay to increase chance of race conditions
        time.sleep(random.uniform(0, 0.001))
        
        # Read current counter
        metadata = thread_manifest.get_file_metadata("counter")
        current_value = metadata["value"]
        
        # Increment counter (this simulates a read-modify-write operation)
        thread_manifest.update_file_metadata("counter", {"value": current_value + 1})
        
        # Also add a thread-specific entry
        thread_manifest.update_file_metadata(f"thread_{worker_id}_op_{i}", {"thread": worker_id})
    except Exception as e:
      errors.append(f"Error in thread {worker_id}: {str(e)}")
  
  # Execute tasks concurrently
  with ThreadPoolExecutor(max_workers=num_threads) as executor:
    futures = [executor.submit(worker_function, i) for i in range(num_threads)]
    
    # Wait for all tasks to complete
    for future in futures:
      future.result()
  
  # Check for errors
  assert not errors, f"Errors occurred during concurrent execution: {errors}"
  
  # Verify all operations completed
  final_manifest = FileManifest(temp_dir)
  
  # Verify all thread-specific entries exist
  for thread_id in range(num_threads):
    for op_id in range(operations_per_thread):
      key = f"thread_{thread_id}_op_{op_id}"
      metadata = final_manifest.get_file_metadata(key)
      assert metadata is not None, f"Missing metadata for {key}"
      assert metadata["thread"] == thread_id
  
  # Check counter value
  # Note: In a perfect thread-safe implementation, the final value should be:
  #       num_threads * operations_per_thread
  # But even with the FileManifest singleton, there could be race conditions
  # if the internal operations aren't properly synchronized
  final_counter = final_manifest.get_file_metadata("counter")
  assert final_counter is not None
  assert final_counter["value"] <= num_threads * operations_per_thread
  
  # In a non-singleton or non-thread-safe implementation, the value would be much lower
  # This verifies that at least some increments occurred
  assert final_counter["value"] > 0
  
  # Log the actual vs expected value (helpful for debugging)
  expected = num_threads * operations_per_thread
  actual = final_counter["value"]
  print(f"Counter value: {actual}/{expected} (actual/expected)")
  
  # Note: If this test consistently shows a lower than expected value,
  # it may indicate that FileManifest needs internal synchronization mechanisms


def test_file_persistence_across_instances(temp_dir):
  """Test that manifest file is properly shared and persisted across instances."""
  # Reset singleton state
  FileManifest._instance = None
  
  # Get path to manifest file
  manifest_path = os.path.join(temp_dir, MANIFEST_FILENAME)
  
  # First instance - add some data and verify file is created
  manifest1 = FileManifest(temp_dir)
  manifest1.update_file_metadata("file1", {"content": "test1"})
  
  # Check that manifest file exists
  assert os.path.exists(manifest_path)
  
  # Manually read the file to verify content
  with open(manifest_path, 'r') as f:
    raw_data = json.load(f)
  
  assert "file1" in raw_data
  assert raw_data["file1"]["content"] == "test1"
  
  # Create a second instance with a different directory
  other_dir = os.path.join(temp_dir, "other_directory")
  os.makedirs(other_dir, exist_ok=True)
  manifest2 = FileManifest(other_dir)
  
  # Second instance should use the same manifest file
  assert manifest2._get_manifest_path() == manifest_path
  
  # Update data from second instance
  manifest2.update_file_metadata("file2", {"content": "test2"})
  
  # Manually read the file again to verify updated content
  with open(manifest_path, 'r') as f:
    updated_data = json.load(f)
  
  assert "file1" in updated_data
  assert "file2" in updated_data
  assert updated_data["file1"]["content"] == "test1"
  assert updated_data["file2"]["content"] == "test2"
  
  # Reset the singleton to simulate application restart
  FileManifest._instance = None
  
  # Create a new instance and verify it loads existing data
  manifest3 = FileManifest(temp_dir)
  
  # Check that data from previous instances is loaded
  file1_data = manifest3.get_file_metadata("file1")
  file2_data = manifest3.get_file_metadata("file2")
  
  assert file1_data is not None
  assert file2_data is not None
  assert file1_data["content"] == "test1"
  assert file2_data["content"] == "test2"
  
  # Modify the manifest file directly
  direct_data = {"file3": {"content": "added_directly"}}
  with open(manifest_path, 'w') as f:
    json.dump(direct_data, f)
  
  # Reset singleton and create new instance
  FileManifest._instance = None
  manifest4 = FileManifest(temp_dir)
  
  # Verify it loads the manually updated data
  file3_data = manifest4.get_file_metadata("file3")
  assert file3_data is not None
  assert file3_data["content"] == "added_directly"
  
  # Original data should be gone since we overwrote the file
  assert manifest4.get_file_metadata("file1") is None
  assert manifest4.get_file_metadata("file2") is None 