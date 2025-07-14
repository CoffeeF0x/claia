"""
Gemma Specialized Demo - Demonstrates specialized behavior with Gemma-3-4B-IT model.

This demo shows specialized model functionality using the larger Gemma 3 4B model
for more complex tasks and specialized behaviors.
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
class GemmaSpecializedDemo:
  """
  Demo class for Gemma-3-4B-IT specialized functionality.

  This demonstrates:
  - Loading the Gemma-3-4B-IT model with specialized behavior
  - Complex reasoning tasks
  - Code generation and analysis
  - Structured output generation
  - Advanced conversation handling
  """

  def __init__(self, session_directory: str, config: ModelConfig):
    """
    Initialize the Gemma specialized demo.

    Args:
        session_directory: Directory for demo session files
        config: Model configuration
    """
    self.session_directory = session_directory
    self.model_name = "gemma-3-4b-it"
    self.registry = ModelRegistry()
    self.config = config

    logger.info(f"Initialized Gemma Specialized Demo with model: {self.model_name}")

  def run(self) -> None:
    """Run the Gemma specialized functionality demo."""
    print(f"\n🧠 Gemma-3-4B-IT Specialized Demo")
    print(f"📁 Session Directory: {self.session_directory}")
    print(f"🎯 Model: {self.model_name}")

    try:
      # Test 1: Code generation and analysis
      print("\n" + "="*60)
      print("TEST 1: Code Generation & Analysis")
      print("="*60)

      code_conversation = self._create_conversation([
        {"role": "user", "content": """Create a Python class for a simple task manager that can:
1. Add tasks with priorities (high, medium, low)
2. Mark tasks as complete
3. List all pending tasks sorted by priority
4. Remove completed tasks

Include proper error handling and docstrings."""}
      ])

      self._run_generation_test("Code Generation", code_conversation)

      # Test 2: Complex reasoning
      print("\n" + "="*60)
      print("TEST 2: Complex Reasoning")
      print("="*60)

      reasoning_conversation = self._create_conversation([
        {"role": "user", "content": """A company has 3 departments: Sales (15 people), Engineering (25 people), and Marketing (10 people).
They want to form cross-functional teams of exactly 5 people each, with at least one person from each department in every team.
How many different teams can be formed? Show your reasoning step by step."""}
      ])

      self._run_generation_test("Complex Reasoning", reasoning_conversation)

      # Test 3: Structured output
      print("\n" + "="*60)
      print("TEST 3: Structured Output Generation")
      print("="*60)

      structured_conversation = self._create_conversation([
        {"role": "user", "content": """Create a detailed project plan for developing a mobile weather app.
Format your response as a structured breakdown with:
- Project overview
- Key features (at least 5)
- Development phases with timelines
- Required technologies
- Risk assessment
- Success metrics

Use clear headers and bullet points."""}
      ])

      self._run_generation_test("Structured Output", structured_conversation)

      # Test 4: Technical problem solving
      print("\n" + "="*60)
      print("TEST 4: Technical Problem Solving")
      print("="*60)

      technical_conversation = self._create_conversation([
        {"role": "user", "content": """I have a Python web application that's experiencing slow database queries.
The app uses SQLAlchemy ORM with PostgreSQL. Users are complaining about 5-10 second load times.
What are the most likely causes and how would you systematically diagnose and fix this issue?
Provide specific code examples where relevant."""}
      ])

      self._run_generation_test("Technical Problem Solving", technical_conversation)

      # Test 5: Creative synthesis
      print("\n" + "="*60)
      print("TEST 5: Creative Synthesis")
      print("="*60)

      creative_conversation = self._create_conversation([
        {"role": "user", "content": """Design a unique board game that combines elements of:
- Resource management (like Settlers of Catan)
- Area control (like Risk)
- Worker placement (like Agricola)
- Cooperative elements (like Pandemic)

Describe the game mechanics, objectives, and what makes it engaging.
Include rules for 2-4 players and estimated play time."""}
      ])

      self._run_generation_test("Creative Synthesis", creative_conversation)

      print(f"\n✅ Gemma-3-4B-IT Specialized Demo completed successfully!")
      print(f"🎓 This demo showcased advanced reasoning, code generation, and structured thinking.")

    except Exception as e:
      print(f"\n❌ Demo failed with error: {str(e)}")
      logger.error(f"Gemma Specialized Demo failed: {str(e)}")

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
    conversation.metadata["demo"] = "gemma_specialized"
    conversation.metadata["model"] = self.model_name
    conversation.metadata["message_count"] = len(messages)
    conversation.metadata["specialized"] = True

    return conversation

  def _run_generation_test(self, test_name: str, conversation: Conversation) -> None:
    """
    Run a single generation test with specialized handling.

    Args:
        test_name: Name of the test for logging
        conversation: Conversation to process
    """
    print(f"\n🔧 {test_name}")
    print("-" * 40)

    # Display the user prompt (truncated if too long)
    last_message = conversation.messages[-1]
    prompt_preview = last_message.content
    if len(prompt_preview) > 100:
      prompt_preview = prompt_preview[:100] + "..."
    print(f"User: {prompt_preview}")
    print()

    try:
      # Run the model with specialized capability detection
      print("🧠 Processing with specialized model...")
      result = self.registry.run(
        model_name=self.model_name,
        conversation=conversation,
        config=self.config
      )

      if result.is_error():
        print(f"❌ Generation failed: {result.message}")
        logger.error(f"{test_name} failed: {result.message}")

        # For demo purposes, show what we attempted
        print(f"💡 This test attempted to demonstrate: {test_name}")
        return

      response = result.data

      # Show response with formatting for readability
      print(f"🤖 Assistant Response:")
      print("-" * 30)
      print(response)
      print("-" * 30)

      # Log success with response length info
      response_length = len(response) if isinstance(response, str) else len(str(response))
      logger.info(f"{test_name} completed successfully - Response length: {response_length} chars")
      print(f"✅ {test_name} completed! (Response: {response_length} characters)")

    except Exception as e:
      print(f"❌ Error during generation: {str(e)}")
      logger.error(f"{test_name} error: {str(e)}")

      # Provide helpful context for debugging
      print(f"💡 Debug info: Model={self.model_name}, Test={test_name}")
      print(f"🔍 Check that the model is available and properly configured.")
