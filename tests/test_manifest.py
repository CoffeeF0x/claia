#!/usr/bin/env python3
"""
Test script for the manifest-based file storage system in CLAIA.
This tests the functionality of storing file metadata in manifest files.
"""

# External dependencies
import os
import sys
import shutil
import logging
import tempfile
from typing import Dict, List, Any, Optional

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Internal dependencies
from conversations.base import BaseFile
from conversations.files import FileFactory, TextFile, ImageFile, AudioFile, VideoFile, DocumentFile, GenericFile
from conversations.config import Config



########################################################################
#                            INITIALIZATION                            #
########################################################################
# Set up logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a temporary directory for testing
TEST_DIR = tempfile.mkdtemp()
FILES_DIR = os.path.join(TEST_DIR, 'files')
CONFIG_DIR = os.path.join(TEST_DIR, 'config')

# Ensure directories exist
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)



########################################################################
#                           HELPER FUNCTIONS                           #
########################################################################
def create_sample_file(filename: str, content: str = None) -> str:
  """
  Create a sample file for testing.

  Args:
      filename: The name of the file to create
      content: Optional content to write to the file

  Returns:
      str: The path to the created file
  """
  file_path = os.path.join(TEST_DIR, filename)

  # Create the file with content or as empty
  with open(file_path, 'w') as f:
    if content:
      f.write(content)

  logger.info(f"Created sample file: {file_path}")
  return file_path


def create_sample_files() -> Dict[str, str]:
  """
  Create sample files of different types for testing.

  Returns:
      Dict[str, str]: A dictionary mapping file type to file path
  """
  files = {}

  # Text file
  files['text'] = create_sample_file('sample.txt',
    "This is a sample text file.\nIt contains multiple lines of text.")

  # HTML file (text type)
  files['html'] = create_sample_file('sample.html',
    "<html><body><h1>Sample HTML</h1><p>This is HTML content.</p></body></html>")

  # JSON file (text type)
  files['json'] = create_sample_file('sample.json',
    '{"name": "Sample", "type": "JSON", "nested": {"key": "value"}}')

  # Empty file (generic type)
  files['empty'] = create_sample_file('empty.bin')

  # Create a fake image file (we're not testing content processing, just the manifest)
  files['image'] = create_sample_file('sample.png', 'Not a real image but has the extension')

  # Create a fake audio file
  files['audio'] = create_sample_file('sample.mp3', 'Not a real audio file but has the extension')

  # Create a fake video file
  files['video'] = create_sample_file('sample.mp4', 'Not a real video file but has the extension')

  # Create a fake document file
  files['document'] = create_sample_file('sample.pdf', 'Not a real PDF but has the extension')

  return files


def create_sample_configs() -> Dict[str, Dict[str, Any]]:
  """
  Create sample configuration data for testing.

  Returns:
      Dict[str, Dict[str, Any]]: A dictionary mapping config ID to config data
  """
  configs = {}

  # Simple config
  configs['simple'] = {
    'name': 'simple-config',
    'title': 'Simple Configuration',
    'description': 'A simple configuration for testing',
    'settings': {
      'enabled': True,
      'value': 42,
      'mode': 'test'
    }
  }

  # Complex config
  configs['complex'] = {
    'name': 'complex-config',
    'title': 'Complex Configuration',
    'description': 'A more complex configuration for testing',
    'settings': {
      'enabled': False,
      'values': [1, 2, 3, 4, 5],
      'nested': {
        'key1': 'value1',
        'key2': 'value2'
      }
    },
    'tags': ['test', 'manifest', 'config']
  }

  return configs


def cleanup():
  """
  Clean up the test directory.
  """
  try:
    shutil.rmtree(TEST_DIR)
    logger.info(f"Cleaned up test directory: {TEST_DIR}")
  except Exception as e:
    logger.error(f"Failed to clean up test directory: {e}")



########################################################################
#                              TEST CASES                              #
########################################################################
def test_file_manifest():
  """
  Test the manifest functionality for files.
  """
  logger.info("Testing file manifest functionality...")

  # Create sample files
  sample_files = create_sample_files()

  # Dictionary to store created file objects
  file_objects = {}

  # 1. Test creating and saving files
  logger.info("1. Testing file creation and saving...")
  for file_type, file_path in sample_files.items():
    # Create a file object using the factory
    file_obj = FileFactory.create_file(file_path, FILES_DIR)

    # Process the file to extract metadata
    file_obj.process()

    # Save the file and its metadata
    saved_path = file_obj.save()

    # Verify the file was saved
    assert saved_path is not None, f"Failed to save {file_type} file"
    assert os.path.exists(saved_path), f"Saved file {saved_path} does not exist"

    # Store the file object for later tests
    file_objects[file_type] = file_obj

    logger.info(f"  - Saved {file_type} file: {saved_path}")

  # 2. Test manifest files were created
  logger.info("2. Testing manifest files were created...")
  for subdir in os.listdir(FILES_DIR):
    subdir_path = os.path.join(FILES_DIR, subdir)
    if os.path.isdir(subdir_path):
      manifest_path = os.path.join(subdir_path, "manifest.json")
      assert os.path.exists(manifest_path), f"Manifest file not found in {subdir_path}"

      # Load the manifest and check its content
      with open(manifest_path, 'r') as f:
        manifest = json.load(f)

      assert isinstance(manifest, dict), f"Manifest in {subdir_path} is not a dictionary"
      logger.info(f"  - Found manifest in {subdir_path} with {len(manifest)} entries")

  # 3. Test loading files from manifest
  logger.info("3. Testing loading files from manifest...")
  for file_type, file_obj in file_objects.items():
    # Load the file using its ID
    loaded_file = FileFactory.load_file(file_obj.file_id, FILES_DIR)

    # Verify the file was loaded correctly
    assert loaded_file is not None, f"Failed to load {file_type} file"
    assert loaded_file.file_id == file_obj.file_id, f"Loaded file ID does not match for {file_type}"
    assert loaded_file.file_name == file_obj.file_name, f"Loaded file name does not match for {file_type}"

    logger.info(f"  - Loaded {file_type} file: {loaded_file.file_name}")

  # 4. Test listing files
  logger.info("4. Testing listing files...")
  all_files = BaseFile.list_files(FILES_DIR)

  # Verify all files are listed
  assert len(all_files) == len(file_objects), f"Expected {len(file_objects)} files, got {len(all_files)}"

  # Print file listing
  logger.info(f"  - Found {len(all_files)} files in listing:")
  for file_info in all_files:
    logger.info(f"    - {file_info['file_name']} ({file_info['subdirectory']})")

  # 5. Test deleting files
  logger.info("5. Testing deleting files...")
  for file_type, file_obj in list(file_objects.items()):
    # Delete the file
    deleted = BaseFile.delete(file_obj.file_id, FILES_DIR)

    # Verify the file was deleted
    assert deleted, f"Failed to delete {file_type} file"

    # Try to load the deleted file
    loaded_file = FileFactory.load_file(file_obj.file_id, FILES_DIR)
    assert loaded_file is None, f"Deleted {file_type} file can still be loaded"

    logger.info(f"  - Deleted {file_type} file: {file_obj.file_name}")

    # Remove from the dictionary
    del file_objects[file_type]

  # Verify all files were deleted
  assert len(file_objects) == 0, f"Not all files were deleted, {len(file_objects)} remain"

  # Check if manifests were updated
  for subdir in os.listdir(FILES_DIR):
    subdir_path = os.path.join(FILES_DIR, subdir)
    if os.path.isdir(subdir_path):
      manifest_path = os.path.join(subdir_path, "manifest.json")
      if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
          manifest = json.load(f)

        assert len(manifest) == 0, f"Manifest in {subdir_path} still has {len(manifest)} entries"

  logger.info("File manifest tests completed successfully!")


def test_config_manifest():
  """
  Test the manifest functionality for configurations.
  """
  logger.info("Testing config manifest functionality...")

  # Create sample configs
  sample_configs = create_sample_configs()

  # Dictionary to store created config objects
  config_objects = {}

  # 1. Test creating and saving configs
  logger.info("1. Testing config creation and saving...")
  for config_id, config_data in sample_configs.items():
    # Create a config object
    config_obj = Config(
      config_id=config_id,
      base_directory=CONFIG_DIR,
      config_type="test-configs",
      **config_data
    )

    # Save the config
    saved_path = config_obj.save_metadata()

    # Verify the config was saved
    assert saved_path is not None, f"Failed to save config {config_id}"

    # Store the config object for later tests
    config_objects[config_id] = config_obj

    logger.info(f"  - Saved config: {config_id}")

  # 2. Test manifest file was created
  logger.info("2. Testing config manifest file was created...")
  manifest_path = os.path.join(CONFIG_DIR, "test-configs", "manifest.json")
  assert os.path.exists(manifest_path), f"Config manifest file not found at {manifest_path}"

  # Load the manifest and check its content
  with open(manifest_path, 'r') as f:
    manifest = json.load(f)

  assert isinstance(manifest, dict), "Config manifest is not a dictionary"
  assert len(manifest) == len(sample_configs), f"Expected {len(sample_configs)} configs in manifest, got {len(manifest)}"
  logger.info(f"  - Found config manifest with {len(manifest)} entries")

  # 3. Test loading configs from manifest
  logger.info("3. Testing loading configs from manifest...")
  for config_id, config_obj in config_objects.items():
    # Load the config
    loaded_config = Config.load(config_id, CONFIG_DIR, "test-configs")

    # Verify the config was loaded correctly
    assert loaded_config is not None, f"Failed to load config {config_id}"
    assert loaded_config.config_id == config_id, f"Loaded config ID does not match for {config_id}"
    assert loaded_config.get("name") == config_obj.get("name"), f"Loaded config name does not match for {config_id}"

    logger.info(f"  - Loaded config: {config_id}")

  # 4. Test listing configs
  logger.info("4. Testing listing configs...")
  all_configs = Config.list_configs(CONFIG_DIR, "test-configs")

  # Verify all configs are listed
  assert len(all_configs) == len(config_objects), f"Expected {len(config_objects)} configs, got {len(all_configs)}"

  # Print config listing
  logger.info(f"  - Found {len(all_configs)} configs in listing:")
  for config_info in all_configs:
    logger.info(f"    - {config_info['config_id']}")

  # 5. Test deleting configs
  logger.info("5. Testing deleting configs...")
  for config_id in list(config_objects.keys()):
    # Delete the config
    deleted = Config.delete(config_id, CONFIG_DIR, "test-configs")

    # Verify the config was deleted
    assert deleted, f"Failed to delete config {config_id}"

    # Try to load the deleted config
    loaded_config = Config.load(config_id, CONFIG_DIR, "test-configs")
    assert loaded_config is None, f"Deleted config {config_id} can still be loaded"

    logger.info(f"  - Deleted config: {config_id}")

  # Check if manifest was updated
  with open(manifest_path, 'r') as f:
    manifest = json.load(f)

  assert len(manifest) == 0, f"Config manifest still has {len(manifest)} entries after deletion"

  logger.info("Config manifest tests completed successfully!")



########################################################################
#                             MAIN FUNCTION                            #
########################################################################
def test_manifest_functionality():
  """
  Main test function for the manifest functionality.
  """
  try:
    # Test file manifest functionality
    test_file_manifest()

    # Test config manifest functionality
    test_config_manifest()

    logger.info("All manifest tests completed successfully!")
    return True
  except Exception as e:
    logger.error(f"Manifest tests failed: {e}")
    import traceback
    traceback.print_exc()
    return False
  finally:
    # Clean up
    cleanup()


if __name__ == "__main__":
  success = test_manifest_functionality()
  sys.exit(0 if success else 1)