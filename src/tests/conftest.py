#####################
# EXTERNAL IMPORTS #
#####################
import pytest
from pathlib import Path


#####################
#     FIXTURES     #
#####################

@pytest.fixture
def test_data_dir():
  """Returns the path to the test data directory."""
  return Path(__file__).parent / "test_data"

@pytest.fixture
def sample_conversation_json():
  """Returns a sample conversation JSON for testing."""
  return {
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Hello!"
      },
      {
        "role": "assistant",
        "content": "Hi there! How can I help you today?"
      }
    ],
    "metadata": {
      "created_at": "2024-03-21T12:00:00Z",
      "model": "test-model"
    }
  }

@pytest.fixture
def test_settings():
  """Returns test settings."""
  return {
    "model": "test-model",
    "api_key": "test-key",
    "temperature": 0.7
  }