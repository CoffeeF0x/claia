"""
Gemma Text Demo - Demonstrates text generation with Gemma-3-1B-IT model.

This demo shows basic text-to-text functionality using the Gemma 3 1B model
for standard conversational AI tasks.
"""

import logging
import os
from datetime import datetime

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
class GemmaTextDemo:
  """
  Demo class for Gemma-3-1B-IT text generation functionality.

  This demonstrates:
  - Loading the Gemma-3-1B-IT model
  - Basic text-to-text conversation
  - Model response generation
  - Error handling
  """

  def __init__(self, session_directory: str, config: ModelConfig):
    """
    Initialize the Gemma text demo.

    Args:
        session_directory: Directory for demo session files
        config: Model configuration
    """
    self.session_directory = session_directory
    self.model_name = "gemma-3-1b-it"
    self.config = config
    self.registry = ModelRegistry()

    logger.info(f"Initialized Gemma Text Demo with model: {self.model_name}")

  def run(self) -> None:
    """Run the Gemma text generation demo."""
    print(f"\n🤖 Gemma-3-1B-IT Text Generation Demo")
    print(f"📁 Session Directory: {self.session_directory}")
    print(f"🎯 Model: {self.model_name}")

    try:
      # Test 1: Simple greeting
      print("\n" + "="*60)
      print("TEST 1: Simple Greeting")
      print("="*60)

      greeting_conversation = self._create_conversation([
        {"role": "user", "content": "Hello! Can you introduce yourself?"}
      ])

      self._run_generation_test("Greeting Test", greeting_conversation)

      # Test 2: Creative writing
      print("\n" + "="*60)
      print("TEST 2: Creative Writing")
      print("="*60)

      creative_conversation = self._create_conversation([
        {"role": "user", "content": "Write a short story about a robot learning to paint. Keep it under 100 words."}
      ])

      self._run_generation_test("Creative Writing Test", creative_conversation)

      # Test 3: Question answering
      print("\n" + "="*60)
      print("TEST 3: Question Answering")
      print("="*60)

      qa_conversation = self._create_conversation([
        {"role": "user", "content": "What are the three primary colors and why are they important in art?"}
      ])

      self._run_generation_test("Question Answering Test", qa_conversation)

      # Test 4: Multi-turn conversation
      print("\n" + "="*60)
      print("TEST 4: Multi-turn Conversation")
      print("="*60)

      multiturn_conversation = self._create_conversation([
        {"role": "user", "content": "I'm learning Python. Can you help me?"},
        {"role": "assistant", "content": "Of course! I'd be happy to help you learn Python. What would you like to know?"},
        {"role": "user", "content": "How do I create a simple function that adds two numbers?"}
      ])

      self._run_generation_test("Multi-turn Conversation Test", multiturn_conversation)

      print(f"\n✅ Gemma-3-1B-IT Text Demo completed successfully!")

    except Exception as e:
      print(f"\n❌ Demo failed with error: {str(e)}")
      logger.error(f"Gemma Text Demo failed: {str(e)}")

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
    conversation.metadata["demo"] = "gemma_text"
    conversation.metadata["model"] = self.model_name
    conversation.metadata["message_count"] = len(messages)

    return conversation

  def _run_generation_test(self, test_name: str, conversation: Conversation) -> None:
    """
    Run a single generation test.

    Args:
        test_name: Name of the test for logging
        conversation: Conversation to process
    """
    print(f"\n🔧 {test_name}")
    print("-" * 40)

    # Display the last user message
    last_message = conversation.messages[-1]
    print(f"User: {last_message.content}")
    print()

    try:
      # Run the model
      print("🤔 Generating response...")
      result = self.registry.run(
        model_name=self.model_name,
        conversation=conversation,
        config=self.config
      )

      if result.is_error():
        print(f"❌ Generation failed: {result.message}")
        logger.error(f"{test_name} failed: {result.message}")
        return

      response = result.data
      print(f"🤖 Assistant: {response}")

      # Log success
      logger.info(f"{test_name} completed successfully")
      print(f"✅ {test_name} completed!")

    except Exception as e:
      print(f"❌ Error during generation: {str(e)}")
      logger.error(f"{test_name} error: {str(e)}")
