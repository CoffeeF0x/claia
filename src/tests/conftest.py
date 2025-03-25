"""
Global pytest configuration for CLAIA tests.
"""

# External dependencies
import pytest
import logging
import tempfile
import shutil
import os
import base64
from PIL import Image

# Internal dependencies
from files import FileManifest, ImageFile


@pytest.fixture
def temp_dir():
  """Create a temporary directory for testing."""
  temp_path = tempfile.mkdtemp()
  yield temp_path
  # Cleanup after test
  if os.path.exists(temp_path):
    shutil.rmtree(temp_path)


@pytest.fixture
def clean_manifest(temp_dir):
  """Create a clean test file manifest for each test."""
  # Reset the singleton to ensure a clean state for each test
  FileManifest._instance = None
  return FileManifest(temp_dir)


@pytest.fixture
def test_text_file(temp_dir):
  """Create a sample text file for testing."""
  file_path = os.path.join(temp_dir, "sample.txt")
  with open(file_path, "w") as f:
    f.write("This is sample text content")
  return file_path


@pytest.fixture
def test_image_file(temp_dir):
  """Create a sample image file for testing."""
  try:
    # Create a simple 100x100 red image
    image_path = os.path.join(temp_dir, "sample.png")
    img = Image.new('RGB', (100, 100), color='red')
    img.save(image_path)
    return image_path
  except ImportError:
    pytest.skip("PIL not available, skipping image tests")


@pytest.fixture
def test_image_path(temp_dir):
  """
  Create a simple test image file with specific format.
  
  This is a very basic 1x1 pixel black image in PNG format.
  """
  # Base64 encoded 1x1 pixel black PNG
  png_data = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFewJ2gP"
    "W+BAAAAABJRU5ErkJggg=="
  )
  
  image_path = os.path.join(temp_dir, "test_image.png")
  with open(image_path, "wb") as f:
    f.write(png_data)
  
  return image_path


@pytest.fixture
def image_file(temp_dir, test_image_path):
  """Create an ImageFile instance for testing."""
  # Create an ImageFile with the test image as a reference file
  img = ImageFile(
    base_directory=temp_dir,
    file_name="test_image.png",
    external_path=test_image_path,
    is_reference=True  # Use as reference to ensure file exists
  )
  return img


@pytest.fixture
def test_file(temp_dir):
  """Create a test text file for BaseFile tests."""
  file_path = os.path.join(temp_dir, "test.txt")
  with open(file_path, "w") as f:
    f.write("This is a test file")
  return file_path


@pytest.fixture
def base_file(temp_dir, test_file):
  """Create a BaseFile instance for testing."""
  # Create a file that's not a reference so we can test copying
  from files import BaseFile
  file = BaseFile(
    base_directory=temp_dir,
    file_name="test.txt",
    external_path=test_file,
    is_reference=False
  )
  return file


@pytest.fixture(autouse=True)
def disable_logging():
  """Disable logging during tests to reduce noise."""
  logging.disable(logging.CRITICAL)
  yield
  logging.disable(logging.NOTSET)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
  """
  Clean the environment for tests by removing environment variables
  that might affect test behavior.
  """
  variables_to_clean = [
    # API keys
    "OPENAI_API_TOKEN",
    "ANTHROPIC_API_TOKEN",
    "LOCAL_LLM_API_TOKEN",
    "RUNPOD_API_TOKEN",
    "MASSED_COMPUTE_API_TOKEN",
    "OPENROUTER_API_TOKEN",
    "HUGGINGFACE_API_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    
    # Directories
    "MODEL_DIRECTORY",
    "PROMPT_DIRECTORY",
    "CONVERSATION_DIRECTORY",
    "MODULES_DIRECTORY",
    "ARTIFACTS_DIRECTORY",
    "CONVERSATION_FILES_DIRECTORY",
    "TEMP_DIRECTORY",
    
    # Other settings
    "ACTIVE_MODEL",
    "ACTIVE_AGENT",
    "DEFAULT_PROMPT_NAME",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_FILE",
  ]
  
  for var in variables_to_clean:
    monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def reset_manifest():
  """Reset the manifest singleton between tests."""
  FileManifest._instance = None
  yield
