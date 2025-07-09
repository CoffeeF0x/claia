"""
CLAIA Conversation Demo

This script demonstrates how to use the CLAIA Conversation class.
"""

# External dependencies
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_dir))

# Internal dependencies
from files import Conversation, BaseFile
from enums.conversation import MessageRole, ActionType, TagType, TagStatus



########################################################################
#                              CONSTANTS                               #
########################################################################
SAMPLE_PROMPT = """You are a helpful assistant. Your goal is to provide accurate,
helpful responses to the user's queries in a friendly and conversational tone."""



########################################################################
#                             SETUP DEMO                               #
########################################################################
def setup_demo():
  """Set up the demo environment."""
  print("Setting up demo environment...")

  # Create a temp directory for our demo
  base_dir = tempfile.mkdtemp(prefix="claia_conversation_demo_")
  print(f"Demo files will be stored in: {base_dir}")

  return base_dir



########################################################################
#                             CONVERSATION                             #
########################################################################
def demo_conversation(base_dir):
  """
  Demonstrate features of the Conversation class.
  """
  print("\n" + "CONVERSATION OPERATIONS".center(70, "-") + "\n")

  # 1. Create a new conversation
  print("1. Creating a new conversation")
  conversation = Conversation.create_conversation(
    base_directory=base_dir,
    title="My First Conversation",
    prompt="You are a helpful assistant. Your goal is to provide accurate, helpful responses to user queries."
  )
  print(f"   - Created conversation: {conversation.title} (ID: {conversation.file_id})")
  print(f"   - Prompt: {conversation.prompt[:50]}...")

  # 2. Add messages to the conversation
  print("\n2. Adding messages to the conversation")
  user_message = conversation.add_message(
    speaker=MessageRole.USER,
    content="Hello! What can you tell me about Python?"
  )
  print(f"   - Added user message: {user_message.content}")

  assistant_message = conversation.add_message(
    speaker=MessageRole.ASSISTANT,
    content="""Python is a high-level, interpreted programming language known for its readability and versatility.
It was created by Guido van Rossum in the late 1980s and has become one of the most popular programming languages.
Python is widely used in data science, web development, automation, and more."""
  )
  print(f"   - Added assistant message: {assistant_message.content[:50]}...")

  # 3. List all messages in the conversation
  print("\n3. Listing messages in the conversation")
  for i, message in enumerate(conversation.messages, 1):
    print(f"   {i}. {message.speaker.value}: {message.content[:50]}...")

  # 4. Update a message
  print("\n4. Updating a message")
  original_content = user_message.content
  new_content = "Hello! Can you explain what Python is and what it's used for?"
  conversation.update_message(user_message.message_id, content=new_content)
  print(f"   - Original message: {original_content}")
  print(f"   - Updated message: {new_content}")

  # Create a sample file to attach
  print("\n5. Creating and attaching a file to a message")
  file_path = os.path.join(base_dir, "python_code.py")
  with open(file_path, "w") as f:
    f.write("print('Hello, Python!')")

  sample_file = BaseFile.from_source(file_path, base_dir)
  print(f"   - Created file with ID: {sample_file.file_id}")

  # Attach the file to a message
  conversation.attach_file(user_message.message_id, sample_file.file_id)
  print(f"   - Attached file {sample_file.file_id} to message {user_message.message_id}")

  # View attached files
  message = conversation.get_message(user_message.message_id)
  print(f"   - Message now has {len(message.file_ids)} attached files: {message.file_ids}")

  # 6. Add tool definitions to the conversation (Using Test Tools)
  print("\n6. Adding tool definitions to the conversation (Using Test Tools)")

  # Add the echo tool definition
  echo_tool = conversation.add_tool_definition(
    name="echo",
    description="Echoes back the provided text.",
    parameters={
      "type": "object",
      "properties": {
        "text": {"type": "string", "description": "The text to echo back."}
      },
      "required": ["text"]
    }
  )
  print(f"   - Added tool: {echo_tool.name} (ID: {echo_tool.tool_id})")
  print(f"   - Description: {echo_tool.description}")

  # Add the reverse_string tool definition
  reverse_tool = conversation.add_tool_definition(
    name="reverse_string",
    description="Reverses the provided string.",
    parameters={
      "type": "object",
      "properties": {
        "input_string": {"type": "string", "description": "The string to reverse."}
      },
      "required": ["input_string"]
    }
  )
  print(f"   - Added tool: {reverse_tool.name} (ID: {reverse_tool.tool_id})")

  # 7. List tool definitions
  print("\n7. Listing tool definitions")
  tools = conversation.get_all_tool_definitions()
  print(f"   - Found {len(tools)} tool definitions:")
  for i, tool in enumerate(tools, 1):
    print(f"   {i}. {tool.name}: {tool.description}")

  # 8. Test the prompt with tool definitions (Renumbered)
  print("\n8. Testing the prompt with tool definitions") # Renumbered

  # Change the prompt to include tool definitions
  conversation.change_prompt("""You are a helpful assistant with access to the following tools:

{tool_definitions}

If you need to call a tool, use the following format:
{tool_format}

Please help the user with their requests.""")

  # Format the prompt
  formatted_prompt = conversation.apply_substitutions(conversation.prompt)

  print("   - Prompt with tool definitions:")
  print("   " + "-" * 50)
  for line in formatted_prompt.split("\n")[:10]:  # Show first 10 lines
    print(f"   {line}")
  print("   " + "-" * 50)

  # 9. Export tool definitions to list format (Renumbered)
  print("\n9. Exporting tool definitions to list format") # Renumbered
  tools_list = conversation.get_tool_definitions_as_list()
  print(f"   - Exported {len(tools_list)} tools as a list format")
  print(f"   - First tool: {tools_list[0]['name']}")

  # 10. Change the conversation title and prompt (Renumbered)
  print("\n10. Changing the conversation title") # Renumbered
  print(f"   - Original title: {conversation.title}")
  conversation.change_title("Python Discussion with Test Tools") # Updated title
  print(f"   - New title: {conversation.title}")

  # 11. View the action history (Renumbered)
  print("\n11. Viewing the action history") # Renumbered
  print(f"   {'Timestamp':<15} {'Action Type':<30} {'Description'}")
  print(f"   {'-'*15} {'-'*30} {'-'*40}")
  for action in conversation.actions:
    # Format timestamp to be more readable
    timestamp = f"{action.timestamp:.0f}"

    # Create a description based on action type and metadata
    description = ""
    if action.action_type == ActionType.CREATE_CONVERSATION:
      description = f"Created conversation with title: {action.metadata.get('title', '')}"
    elif action.action_type == ActionType.CREATE_MESSAGE:
      description = f"{action.metadata.get('speaker', '')} message: {action.metadata.get('content_preview', '')}"
    elif action.action_type == ActionType.UPDATE_MESSAGE:
      description = f"Updated message: {action.metadata.get('content_preview', '')}"
    elif action.action_type == ActionType.CHANGE_TITLE:
      description = f"Changed title from '{action.metadata.get('old_title', '')}' to '{action.metadata.get('new_title', '')}'"
    elif action.action_type == ActionType.CHANGE_PROMPT:
      description = f"Changed prompt"
    elif action.action_type == ActionType.ATTACH_FILE:
      description = f"Attached file {action.metadata.get('file_id', '')}"
    elif action.action_type == ActionType.ADD_TOOL_DEFINITION:
      description = f"Added tool: {action.metadata.get('name', '')}"
    elif action.action_type == ActionType.UPDATE_TOOL_DEFINITION:
      description = f"Updated tool: {action.metadata.get('new_name', '')}"
    elif action.action_type == ActionType.REMOVE_TOOL_DEFINITION:
      description = f"Removed tool: {action.metadata.get('name', '')}"
    elif action.action_type == ActionType.PROCESS_FUNCTION_CALL: # Handle new action type
        meta = action.metadata
        if meta.get("error"):
            description = f"Failed tool call: {meta.get('tool_name', 'unknown')} - {meta.get('error')}"
        else:
            description = f"Executed tool call: {meta.get('tool_name', 'unknown')} -> {meta.get('result_preview', '')}"
    else:
      description = str(action.metadata)

    print(f"   {timestamp:<15} {action.action_type.name:<30} {description}")

  # 12. Save and reload the conversation (Renumbered)
  print("\n12. Saving and reloading the conversation") # Renumbered
  conversation.save()
  print(f"   - Saved conversation to: {conversation.path}")
  reloaded_conversation = Conversation.load_conversation(conversation.file_id, base_dir)
  if reloaded_conversation:
    print(f"   - Reloaded conversation: {reloaded_conversation.title}")
    print(f"   - Message count: {len(reloaded_conversation.messages)}")
    print(f"   - Tool count: {len(reloaded_conversation.tool_definitions)}")
    print(f"   - Action count: {len(reloaded_conversation.actions)}")
  else:
    print("   - Failed to reload conversation")

  # 13. Demonstrating bulk loading of tool definitions (Renumbered)
  print("\n13. Demonstrating bulk loading of tool definitions") # Renumbered

  # Create a new conversation
  bulk_conversation = Conversation.create_conversation(
    base_directory=base_dir,
    title="Bulk Tool Loading Demo"
  )

  # Define multiple tools to load at once
  bulk_tools = [
    {
      "name": "search_products",
      "description": "Search for products in the catalog",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "category": {"type": "string", "enum": ["electronics", "books", "clothing"]}
        },
        "required": ["query"]
      }
    },
    {
      "name": "get_product_details",
      "description": "Get detailed information about a product",
      "parameters": {
        "type": "object",
        "properties": {
          "product_id": {"type": "string"}
        },
        "required": ["product_id"]
      }
    },
    {
      "name": "add_to_cart",
      "description": "Add a product to the shopping cart",
      "parameters": {
        "type": "object",
        "properties": {
          "product_id": {"type": "string"},
          "quantity": {"type": "integer", "default": 1}
        },
        "required": ["product_id"]
      }
    }
  ]

  # Load the tools
  loaded_tools = bulk_conversation.load_tool_definitions_from_list(bulk_tools)
  print(f"   - Loaded {len(loaded_tools)} tools in bulk")
  for tool in loaded_tools:
    print(f"   - {tool.name}: {tool.description}")

  # Save this conversation too
  bulk_conversation.save()
  print(f"   - Saved bulk conversation to: {bulk_conversation.path}")

  # 14. Demonstrate Tag Processing with Custom Formats (Renumbered)
  print("\n14. Demonstrating Tag Processing with Custom Formats") # Renumbered

  # Define custom tag formats
  custom_formats = {
    TagType.TOOL_CALL: ("<tool_call>", "</tool_call>"),
    TagType.THINKING: ("<think>", "</think>")
  }
  print(f"   - Defining custom formats: {custom_formats}")

  # Create a conversation with custom tag formats
  tag_convo = Conversation.create_conversation(
    base_directory=base_dir,
    title="Custom Tag Demo",
    prompt="Assistant using custom tags.",
    custom_tag_formats=custom_formats
  )
  # Add echo tool definition needed for the test message
  tag_convo.add_tool_definition(
      name="echo", description="Echoes text", parameters={"type":"object", "properties":{"text":{"type":"string"}}, "required":["text"]}
  )
  print(f"   - Created conversation with custom tags: {tag_convo.title} (ID: {tag_convo.file_id})")

  # Add a message with custom tags (using 'echo' tool)
  message_content_with_tags = "Okay, I need to test the echo. <think>User wants to echo 'Hello World'. I should use the tool.</think> Let me try that: <tool_call>{\"name\": \"echo\", \"parameters\": {\"text\": \"Hello World\"}}</tool_call> How did that work?"
  tag_convo.add_message(
    speaker=MessageRole.ASSISTANT,
    content=message_content_with_tags
  )
  print(f"   - Added message with custom tags: '{message_content_with_tags[:60]}...'")

  # Find the tags in the message content (demonstrates find_tags)
  print("   - Finding tags in the message content:")
  found_tags = tag_convo.find_tags(message_content_with_tags) # Use find_tags here

  # Print the found tags
  if found_tags:
    for tag_info in found_tags:
      # Only print closed tags for brevity in this step
      if tag_info['status'] == TagStatus.CLOSED:
          print(f"     - Found Closed Tag:")
          print(f"       - Type: {tag_info['type'].name}")
          print(f"       - Format: {tag_info['opening_tag']}...{tag_info['closing_tag']}")
          print(f"       - Content: '{tag_info['content']}'")
          print(f"       - Indices: {tag_info['start_index']} - {tag_info['end_index']}")
      else:
          print(f"     - Found Non-Closed Tag:")
          print(f"       - Type: {tag_info['type'].name}")
          print(f"       - Status: {tag_info['status'].name}")
          print(f"       - Opening Tag: {tag_info['opening_tag']}")
          print(f"       - Start Index: {tag_info['start_index']}")

  else:
    print("     - No tags found.")

  # 15. Demonstrate Processing and Executing Tool Calls (New Step)
  print("\n15. Demonstrating Processing and Executing Tool Calls") # New Step
  print(f"   - Original content: '{message_content_with_tags}'")

  # Process the content to execute tool calls
  processed_content = tag_convo.process_tool_calls_in_content(message_content_with_tags)
  print(f"   - Processed content: '{processed_content}'") # Show content with tag replaced

  # Add the processed message to the conversation for context
  tag_convo.add_message(
      speaker=MessageRole.SYSTEM, # Or TOOL role if you add one
      content=f"Tool execution result integrated: {processed_content}"
  )

  # Save this conversation to persist custom formats and processed message
  tag_convo.save()
  print(f"   - Saved custom tag conversation to: {tag_convo.path}")

  # Reload to verify (optional check)
  reloaded_tag_convo = Conversation.load_conversation(tag_convo.file_id, base_dir)
  if reloaded_tag_convo:
      print("   - Custom tag conversation reloaded successfully.")
  else:
      print("   - Failed to reload custom tag conversation.")

  # 16. List all conversations (Renumbered)
  print("\n16. Listing all conversations") # Renumbered
  conversations = Conversation.list_conversations(base_dir)
  print(f"   - Found {len(conversations)} conversations")

  for conversation in conversations:
    title = conversation["metadata"].get("title", "Untitled")
    conv_id = conversation.get("file_id", "Unknown")
    message_count = conversation["metadata"].get("message_count", 0)
    tool_count = conversation["metadata"].get("tool_count", 0)
    has_custom = conversation["metadata"].get("has_custom_tags", False) # Get custom tag flag
    custom_tag_str = ", Custom Tags" if has_custom else "" # Create string if true
    print(f"   - {title} (ID: {conv_id}, {message_count} messages, {tool_count} tools{custom_tag_str})") # Added custom tag info



########################################################################
#                               MAIN                                   #
########################################################################
def main():
  """Run the demo."""
  # Set up the demo
  base_dir = setup_demo()

  try:
    # Demonstrate conversation operations
    demo_conversation(base_dir)
    print("\nDemo processes completed successfully!")

  except Exception as e:
    print(f"Error during demo: {e}")
    import traceback
    traceback.print_exc()

  finally:
    # Clean up the demo directory
    print("\nCleaning up demo environment...")
    if os.path.exists(base_dir):
      shutil.rmtree(base_dir)
    print("Demo complete!")


if __name__ == "__main__":
  main()