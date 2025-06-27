"""
Tests for the Prompt class.
"""

# External dependencies
import pytest
import os
import json
import tempfile
import time
import uuid
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Internal dependencies
from files import Prompt, BaseFile
from enums import FileSubdirectory



########################################################################
#                              FIXTURES                                #
########################################################################
@pytest.fixture
def temp_dir():
  """Create a temporary directory for testing."""
  temp_path = tempfile.mkdtemp()
  yield temp_path
  # Clean up temp directory
  try:
    import shutil
    shutil.rmtree(temp_path)
  except:
    pass

@pytest.fixture
def sample_prompt_data():
  """Sample prompt data for testing."""
  return {
    "name": "test-prompt",
    "prompt": "This is a test prompt with placeholders: {{name}} and {{age}}"
  }

@pytest.fixture
def prompt_file(temp_dir, sample_prompt_data):
  """Create a sample prompt file for testing."""
  prompt = Prompt.create_prompt(
    base_directory=temp_dir,
    prompt_name=sample_prompt_data["name"],
    prompt_text=sample_prompt_data["prompt"]
  )
  return prompt



########################################################################
#                             PROMPT TESTS                             #
########################################################################
def test_create_prompt(temp_dir, sample_prompt_data):
  """Test creating a prompt file."""
  prompt = Prompt.create_prompt(
    base_directory=temp_dir,
    prompt_name=sample_prompt_data["name"],
    prompt_text=sample_prompt_data["prompt"]
  )

  assert prompt is not None
  assert prompt.prompt_name == "test-prompt"
  assert prompt.prompt_text == sample_prompt_data["prompt"]
  assert prompt.file_name.endswith(".json")
  assert prompt.exists()

  # Verify the file content
  with open(prompt.path, 'r') as f:
    content = json.load(f)
    assert content["name"] == sample_prompt_data["name"]
    assert content["prompt"] == sample_prompt_data["prompt"]


def test_validate_prompt_name():
  """Test validation of prompt names."""
  test_cases = [
    ("Simple Name", "simple-name"),
    ("Complex-NAME with SPACES!", "complex-name-with-spaces"),
    ("special@#$%^&*chars", "specialchars"),
    ("multiple--hyphens", "multiple-hyphens"),
    ("-leading-hyphen", "leading-hyphen"),
    ("trailing-hyphen-", "trailing-hyphen"),
    ("", ""),
    (None, "")
  ]

  for input_name, expected_output in test_cases:
    result = Prompt.validate_prompt_name(input_name)
    assert result == expected_output


def test_load_prompt(temp_dir):
  """Test loading a prompt by name."""
  # Create a prompt first
  prompt_name = "test-load-prompt"
  prompt_text = "This is a test prompt for loading"

  original_prompt = Prompt.create_prompt(
    base_directory=temp_dir,
    prompt_name=prompt_name,
    prompt_text=prompt_text
  )

  # Mock the base load method to return a dictionary with the expected structure
  mock_load_result = {
    "metadata": {
      "file_id": original_prompt.file_id,
      "file_name": original_prompt.file_name,
      "mime_type": "application/json",
      "timestamp": time.time(),
      "metadata": {
        "prompt_name": prompt_name,
        "prompt_text_preview": prompt_text[:50] + "..." if len(prompt_text) > 50 else prompt_text
      }
    },
    "content": json.dumps({
      "name": prompt_name,
      "prompt": prompt_text
    })
  }

  with patch.object(BaseFile, 'load', return_value=mock_load_result):
    # Test loading by name
    loaded_prompt = Prompt.load_prompt(prompt_name, temp_dir)

    assert loaded_prompt is not None
    assert loaded_prompt.prompt_name == prompt_name
    assert loaded_prompt.prompt_text == prompt_text
    assert loaded_prompt.file_id == original_prompt.file_id

    # Test loading with different case and spacing
    alt_name = "Test Load Prompt"
    loaded_prompt_alt = Prompt.load_prompt(alt_name, temp_dir)

    assert loaded_prompt_alt is not None
    assert loaded_prompt_alt.prompt_name == prompt_name

    # Test loading non-existent prompt
    with patch.object(Prompt, 'find_files_by_criteria', return_value={}):
      not_found = Prompt.load_prompt("nonexistent-prompt", temp_dir)
      assert not_found is None