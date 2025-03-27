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
    """Demonstrate operations with conversation files."""
    print("\n" + "-" * 70)
    print("CONVERSATION OPERATIONS")
    print("-" * 70)
    
    # Create a new conversation
    print("\n1. Creating a new conversation")
    conversation = Conversation.create_conversation(
        base_directory=base_dir,
        title="My First Conversation",
        prompt=SAMPLE_PROMPT
    )
    print(f"   - Created conversation: {conversation.title} (ID: {conversation.file_id})")
    print(f"   - Prompt: {conversation.prompt[:50]}..." if len(conversation.prompt) > 50 else conversation.prompt)
    
    # Add messages to the conversation
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
    
    # Print all messages
    print("\n3. Listing messages in the conversation")
    for i, message in enumerate(conversation.messages, 1):
        preview = message.content[:50] + "..." if len(message.content) > 50 else message.content
        print(f"   {i}. {message.speaker.value}: {preview}")
    
    # Update a message
    print("\n4. Updating a message")
    print(f"   - Original message: {user_message.content}")
    
    updated_message = conversation.update_message(
        message_id=user_message.message_id,
        content="Hello! Can you explain what Python is and what it's used for?"
    )
    print(f"   - Updated message: {updated_message.content}")
    
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
    
    # Change the conversation title
    print("\n6. Changing the conversation title")
    print(f"   - Original title: {conversation.title}")
    
    conversation.change_title("Python Discussion")
    print(f"   - New title: {conversation.title}")
    
    # Change the conversation prompt
    print("\n7. Changing the conversation prompt")
    print(f"   - Original prompt: {conversation.prompt[:50]}...")
    
    conversation.change_prompt("You are a Python expert assistant. Provide detailed explanations about Python concepts.")
    print(f"   - New prompt: {conversation.prompt[:50]}...")
    
    # View the action history
    print("\n8. Viewing the action history")
    print(f"   {'Timestamp':<15} {'Action Type':<25} {'Description'}")
    print(f"   {'-'*15} {'-'*25} {'-'*50}")
    
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
        else:
            description = str(action.metadata)
        
        print(f"   {timestamp:<15} {action.action_type.name:<25} {description}")
    
    # Save and reload the conversation
    print("\n9. Saving and reloading the conversation")
    conversation.save()
    print(f"   - Saved conversation to: {conversation.path}")
    
    # Reload the conversation
    reloaded_conversation = Conversation.load_conversation(conversation.file_id, base_dir)
    print(f"   - Reloaded conversation: {reloaded_conversation.title}")
    print(f"   - Message count: {len(reloaded_conversation.messages)}")
    print(f"   - Action count: {len(reloaded_conversation.actions)}")
    
    # List all conversations
    print("\n10. Listing all conversations")
    all_conversations = Conversation.list_conversations(base_dir)
    print(f"   - Found {len(all_conversations)} conversations")
    
    for conv_metadata in all_conversations:
        title = conv_metadata.get("title", "Untitled")
        conv_id = conv_metadata.get("file_id", "Unknown")
        message_count = conv_metadata.get("metadata", {}).get("message_count", 0)
        print(f"   - {title} (ID: {conv_id}, {message_count} messages)")
    
    return conversation



########################################################################
#                               MAIN                                   #
########################################################################
def main():
    """Run the demo."""
    # Set up the demo
    base_dir = setup_demo()
    
    try:
        # Demonstrate conversation operations
        conversation = demo_conversation(base_dir)
        
        print("\nDemo completed successfully!")
    
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up the demo directory
        print("\nCleaning up demo environment...")
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        print("Demo completed!")


if __name__ == "__main__":
    main() 