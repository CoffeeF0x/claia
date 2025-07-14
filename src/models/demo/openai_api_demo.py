"""
OpenAI API Demo - Demonstrates various OpenAI models via API.

This demo shows API-based model functionality using different OpenAI models
to showcase their varying capabilities and use cases.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

# Internal dependencies
from common.files.conversation import Conversation
from common.enums.model import ModelCapability
from common.enums.conversation import MessageRole
from common.results import Result
from ..config import ModelConfig

# Import our refactored registry
from models import ModelRegistry


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               DEMO CLASS                             #
########################################################################
class OpenAIAPIDemo:
  """
  Demo class for OpenAI API models functionality.

  This demonstrates:
  - Multiple OpenAI models (GPT-4, GPT-3.5-turbo, GPT-4-turbo)
  - API-based model calls
  - Different model capabilities and use cases
  - Error handling for API calls
  - Model comparison
  """

  def __init__(self, session_directory: str, config: ModelConfig):
    """Initialize the OpenAI API demo."""
    self.session_directory = session_directory
    self.config = config
    self.registry = ModelRegistry()

    # Define models to test (in order of preference/capability)
    self.test_models = [
      ("gpt-4", "GPT-4", "Most capable model for complex reasoning"),
      ("gpt-4-turbo", "GPT-4 Turbo", "Latest model with enhanced capabilities"),
      ("gpt-3.5-turbo", "GPT-3.5 Turbo", "Fast and efficient for general tasks")
    ]

    logger.info("Initialized OpenAI API Demo")

  def run(self) -> None:
    """Run the OpenAI API models demo."""
    print(f"\n🤖 OpenAI API Models Demo")
    print(f"📁 Session Directory: {self.session_directory}")
    print(f"🌐 Testing API-based models")

    # Check API key availability
    if not self.check_api_availability():
      print("\n❌ OpenAI API key not found!")
      print("Please set your OpenAI API key in the OPENAI_API_KEY environment variable.")
      return

    try:
      # Test 1: Model comparison on same task
      print("\n" + "="*70)
      print("TEST 1: Model Comparison - Creative Writing")
      print("="*70)

      creative_prompt = "Write a haiku about artificial intelligence and creativity."
      self._run_model_comparison_test("Creative Writing", creative_prompt)

      # Test 2: Complex reasoning with best model
      print("\n" + "="*70)
      print("TEST 2: Complex Reasoning (Best Available Model)")
      print("="*70)

      reasoning_conversation = self._create_conversation([
        {"role": "user", "content": """Solve this logic puzzle:
Three friends - Alice, Bob, and Carol - each have a different pet (cat, dog, fish) and like different colors (red, blue, green).
Clues:
1. Alice doesn't like red
2. The person with the cat likes blue
3. Bob doesn't have the fish
4. Carol likes green
5. The person with the dog doesn't like blue

Who has which pet and likes which color?"""}
      ])

      best_model = self._get_best_available_model()
      if best_model:
        self._run_single_model_test(f"Logic Puzzle ({best_model[1]})", best_model[0], reasoning_conversation)

      # Test 3: Code generation
      print("\n" + "="*70)
      print("TEST 3: Code Generation")
      print("="*70)

      code_conversation = self._create_conversation([
        {"role": "user", "content": """Create a Python function that:
1. Takes a list of numbers
2. Returns the second largest unique number
3. Handles edge cases (empty list, duplicates, single element)
4. Include docstring and type hints
5. Add 2-3 test cases"""}
      ])

      if best_model:
        self._run_single_model_test(f"Code Generation ({best_model[1]})", best_model[0], code_conversation)

      # Test 4: Conversational AI
      print("\n" + "="*70)
      print("TEST 4: Multi-turn Conversation")
      print("="*70)

      conversation = self._create_conversation([
        {"role": "user", "content": "I'm planning a weekend trip to a city I've never been to. Can you help me plan?"},
        {"role": "assistant", "content": "I'd be happy to help you plan your weekend trip! To give you the best recommendations, could you tell me which city you're visiting and what kinds of activities you enjoy?"},
        {"role": "user", "content": "I'm going to Seattle. I love coffee, music, and outdoor activities when weather permits."}
      ])

      # Use a faster model for conversation
      conversation_model = self._get_fastest_model()
      if conversation_model:
        self._run_single_model_test(f"Travel Planning ({conversation_model[1]})", conversation_model[0], conversation)

      print(f"\n✅ OpenAI API Demo completed successfully!")
      print(f"🎯 Tested {len([m for m in self.test_models if self._is_model_available(m[0])])} OpenAI models")

    except Exception as e:
      print(f"\n❌ Demo failed with error: {str(e)}")
      logger.error(f"OpenAI API Demo failed: {str(e)}")

  def check_api_availability(self) -> bool:
    """Check if OpenAI API key is available."""
    if not self.config.has_api_token('openai'):
      print("\n❌ OpenAI API key not found!")
      print("Please set your OpenAI API key in the OPENAI_API_KEY environment variable.")
      return False
    return True

  def _is_model_available(self, model_name: str) -> bool:
    """
    Check if a model is available for use.

    Args:
        model_name: Name of the model to check

    Returns:
        True if model is available, False otherwise
    """
    try:
      available_sources = self.registry.find_available_sources(model_name)
      return "openai" in available_sources
    except:
      return False

  def _get_best_available_model(self):
    """Get the best available OpenAI model."""
    for model_info in self.test_models:
      if self._is_model_available(model_info[0]):
        return model_info
    return None

  def _get_fastest_model(self):
    """Get the fastest available OpenAI model (usually GPT-3.5-turbo)."""
    # Check from fastest to slowest
    for model_info in reversed(self.test_models):
      if self._is_model_available(model_info[0]):
        return model_info
    return None

  def _create_conversation(self, messages: list) -> Conversation:
    """
    Create a conversation object from message list.

    Args:
        messages: List of message dictionaries with 'role' and 'content'

    Returns:
        Conversation object
    """
    conversation = Conversation(base_directory=self.session_directory)

    for msg in messages:
      conversation.add_message(
        speaker=MessageRole(msg["role"]),
        content=msg["content"]
      )

    # Set some metadata
    conversation.metadata["demo"] = "openai_api"
    conversation.metadata["message_count"] = len(messages)

    return conversation

  def _run_model_comparison_test(self, test_name: str, prompt: str) -> None:
    """
    Run the same prompt across multiple models for comparison.

    Args:
        test_name: Name of the test for logging
        prompt: Prompt to send to each model
    """
    print(f"\n🔬 {test_name} - Model Comparison")
    print(f"📝 Prompt: {prompt}")
    print("-" * 50)

    conversation = self._create_conversation([
      {"role": "user", "content": prompt}
    ])

    tested_models = 0
    for model_name, model_display, model_description in self.test_models:
      if self._is_model_available(model_name):
        print(f"\n🤖 Testing {model_display}")
        print(f"💡 {model_description}")

        try:
          result = self.registry.run(
            model_name=model_name,
            conversation=conversation,
            config=self.config
          )

          if result.is_error():
            print(f"❌ {model_display} failed: {result.message}")
          else:
            response = result.data
            print(f"📤 Response: {response}")
            tested_models += 1

        except Exception as e:
          print(f"❌ Error with {model_display}: {str(e)}")

        print("-" * 30)

    if tested_models == 0:
      print("❌ No models were available for testing")
    else:
      print(f"✅ Tested {tested_models} models successfully")

  def _run_single_model_test(self, test_name: str, model_name: str, conversation: Conversation) -> None:
    """
    Run a single model test.

    Args:
        test_name: Name of the test for logging
        model_name: Model to use
        conversation: Conversation to process
    """
    print(f"\n🔧 {test_name}")
    print("-" * 40)

    # Display the last user message (truncated if too long)
    last_message = conversation.messages[-1]
    prompt_preview = last_message.content
    if len(prompt_preview) > 150:
      prompt_preview = prompt_preview[:150] + "..."
    print(f"User: {prompt_preview}")
    print()

    try:
      print(f"🌐 Calling OpenAI API with {model_name}...")
      result = self.registry.run(
        model_name=model_name,
        conversation=conversation,
        config=self.config
      )

      if result.is_error():
        print(f"❌ API call failed: {result.message}")
        logger.error(f"{test_name} failed: {result.message}")
        return

      response = result.data

      # Show response with formatting for readability
      print(f"🤖 Assistant Response:")
      print("-" * 30)
      print(response)
      print("-" * 30)

      # Log success with response info
      response_length = len(response) if isinstance(response, str) else len(str(response))
      logger.info(f"{test_name} completed successfully - Response length: {response_length} chars")
      print(f"✅ {test_name} completed! (Response: {response_length} characters)")

    except Exception as e:
      print(f"❌ Error during API call: {str(e)}")
      logger.error(f"{test_name} error: {str(e)}")

      # Provide helpful context for debugging
      print(f"💡 Debug info: Model={model_name}, Test={test_name}")
      if "api_key" in str(e).lower():
        print(f"🔑 This might be an API key issue. Check your OpenAI API key configuration.")
