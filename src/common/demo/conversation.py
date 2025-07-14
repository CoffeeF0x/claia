"""
Conversation demonstration functionality.
"""

from common.files.conversation.conversation import Conversation
from common.files.conversation.conversation_settings import ConversationSettings
from common.enums.conversation import MessageRole


class ConversationDemo:
  """Demo class for Conversation functionality."""

  def __init__(self, session_dir: str):
    """Initialize with session directory."""
    self.session_dir = session_dir

  def run(self):
    """Demonstrate Conversation functionality."""
    print("\n=== Conversation Demo ===")
    print("Conversation manages structured chat conversations with messages, actions, and tools.")

    try:
      # Create a conversation
      conversation = Conversation(
        base_directory=self.session_dir,
        file_name="demo_conversation",
        title="Demo Conversation",
        prompt="You are a helpful AI assistant demonstrating conversation functionality."
      )

      print(f"✓ Created Conversation: {conversation.title}")
      print(f"  - File: {conversation.file_name}")
      print(f"  - Prompt: {conversation.prompt}")

      # Add messages
      user_msg = conversation.add_message(
        speaker=MessageRole.USER,
        content="Hello! Can you tell me about the weather?"
      )
      print(f"✓ Added user message: {user_msg.message_id}")

      assistant_msg = conversation.add_message(
        speaker=MessageRole.ASSISTANT,
        content="I'd be happy to help with weather information! However, I don't have access to current weather data. You might want to check a weather service."
      )
      print(f"✓ Added assistant message: {assistant_msg.message_id}")

      # Add a tool definition
      tool_def = conversation.add_tool_definition(
        name="get_weather",
        description="Get current weather for a location",
        parameters={
          "type": "object",
          "properties": {
            "location": {"type": "string", "description": "The location to get weather for"}
          },
          "required": ["location"]
        }
      )
      print(f"✓ Added tool definition: {tool_def.name}")

      # Update settings
      settings = ConversationSettings()
      settings.text_settings["temperature"] = 0.7
      settings.text_settings["max_tokens"] = 1000
      conversation.update_settings(settings)
      print("✓ Updated conversation settings")

      # Save the conversation
      saved_path = conversation.save()
      if saved_path:
        print(f"✓ Conversation saved to: {saved_path}")

        # Show summary
        print(f"✓ Conversation summary:")
        print(f"  - Messages: {len(conversation.messages)}")
        print(f"  - Actions: {len(conversation.actions)}")
        print(f"  - Tool definitions: {len(conversation.tool_definitions)}")

    except Exception as e:
      print(f"✗ Error in Conversation demo: {e}")
