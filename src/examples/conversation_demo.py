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
from enums.conversation import MessageRole, ActionType



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
  
  # 6. Add tool definitions to the conversation
  print("\n6. Adding tool definitions to the conversation")
  
  # Add a weather tool definition
  weather_tool = conversation.add_tool_definition(
    name="get_weather",
    description="Get the current weather for a location",
    parameters={
      "type": "object",
      "properties": {
        "location": {"type": "string", "description": "City name or zip code"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
      },
      "required": ["location"]
    }
  )
  print(f"   - Added tool: {weather_tool.name} (ID: {weather_tool.tool_id})")
  print(f"   - Description: {weather_tool.description}")
  
  # Add a calculator tool definition
  calculator_tool = conversation.add_tool_definition(
    name="calculate",
    description="Perform a calculation",
    parameters={
      "type": "object",
      "properties": {
        "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
        "x": {"type": "number"},
        "y": {"type": "number"}
      },
      "required": ["operation", "x", "y"]
    }
  )
  print(f"   - Added tool: {calculator_tool.name} (ID: {calculator_tool.tool_id})")
  
  # 7. List tool definitions
  print("\n7. Listing tool definitions")
  tools = conversation.get_all_tool_definitions()
  print(f"   - Found {len(tools)} tool definitions:")
  for i, tool in enumerate(tools, 1):
    print(f"   {i}. {tool.name}: {tool.description}")
  
  # 8. Update a tool definition
  print("\n8. Updating a tool definition")
  conversation.update_tool_definition(
    tool_id=weather_tool.tool_id,
    description="Get detailed weather information for a location",
    parameters={
      "type": "object",
      "properties": {
        "location": {"type": "string", "description": "City name, zip code, or coordinates"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"},
        "include_forecast": {"type": "boolean", "default": False}
      },
      "required": ["location"]
    }
  )
  
  # Get the updated tool
  updated_tool = conversation.get_tool_definition(weather_tool.tool_id)
  print(f"   - Original description: {weather_tool.description}")
  print(f"   - Updated description: {updated_tool.description}")
  print(f"   - Added parameter: include_forecast")
  
  # 9. Test the prompt with tool definitions
  print("\n9. Testing the prompt with tool definitions")
  
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
  
  # 10. Remove a tool definition
  print("\n10. Removing a tool definition")
  result = conversation.remove_tool_definition(calculator_tool.tool_id)
  print(f"   - Removed calculator tool: {result}")
  
  remaining_tools = conversation.get_all_tool_definitions()
  print(f"   - Remaining tools: {len(remaining_tools)}")
  for tool in remaining_tools:
    print(f"   - {tool.name}")
  
  # 11. Export tool definitions to list format
  print("\n11. Exporting tool definitions to list format")
  tools_list = conversation.get_tool_definitions_as_list()
  print(f"   - Exported {len(tools_list)} tools as a list format")
  print(f"   - First tool: {tools_list[0]['name']}")
  
  # 12. Change the conversation title and prompt
  print("\n12. Changing the conversation title")
  print(f"   - Original title: {conversation.title}")
  
  conversation.change_title("Python Discussion with Tools")
  print(f"   - New title: {conversation.title}")
  
  # 13. View the action history
  print("\n13. Viewing the action history")
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
    else:
      description = str(action.metadata)
    
    print(f"   {timestamp:<15} {action.action_type.name:<30} {description}")
  
  # 14. Save and reload the conversation
  print("\n14. Saving and reloading the conversation")
  conversation.save()
  print(f"   - Saved conversation to: {conversation.path}")
  
  # Reload the conversation
  reloaded_conversation = Conversation.load_conversation(conversation.file_id, base_dir)
  print(f"   - Reloaded conversation: {reloaded_conversation.title}")
  print(f"   - Message count: {len(reloaded_conversation.messages)}")
  print(f"   - Tool count: {len(reloaded_conversation.tool_definitions)}")
  print(f"   - Action count: {len(reloaded_conversation.actions)}")
  
  # 15. Demonstrating bulk loading of tool definitions
  print("\n15. Demonstrating bulk loading of tool definitions")
  
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
  
  # 16. List all conversations
  print("\n16. Listing all conversations")
  
  # Use the list_conversations method to list conversations
  conversations = Conversation.list_conversations(base_dir)
  print(f"   - Found {len(conversations)} conversations")
  
  for conversation_metadata in conversations:
    title = conversation_metadata.get("title", "Untitled")
    conv_id = conversation_metadata.get("file_id", "Unknown")
    message_count = conversation_metadata.get("message_count", 0)
    tool_count = conversation_metadata.get("tool_count", 0)
    print(f"   - {title} (ID: {conv_id}, {message_count} messages, {tool_count} tools)")
  



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