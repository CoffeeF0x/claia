"""
Utility functions for tool call text manipulation.

These are pure string processing functions that can be used to find and
validate tool calls in message content.
"""

# External dependencies
from typing import List, Dict, Any
import json
import logging


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                           UTILITY FUNCTIONS                          #
########################################################################
def find_tool_calls(content: str, start_token: str, end_token: str) -> List[Dict[str, Any]]:
    """
    Find tool call spans in text delimited by the given start/end tokens.

    Tokens are matched literally and non-overlapping, scanning left-to-right.
    This is a pure string processing function with no dependencies on conversation objects.

    Args:
        content: The text content to search
        start_token: The literal start token (e.g., "[TOOL_CALL]")
        end_token: The literal end token (e.g., "[/TOOL_CALL]")

    Returns:
        List[Dict]: Each dict contains:
            {
                "start_index": int,    # index of the start token
                "end_index": int,      # index after the end token
                "content": str,        # text between the tokens
                "full_text": str       # text including the tokens
            }

    Example:
        >>> text = "Hello [TOOL_CALL]{'name': 'test'}[/TOOL_CALL] world"
        >>> calls = find_tool_calls(text, "[TOOL_CALL]", "[/TOOL_CALL]")
        >>> len(calls)
        1
        >>> calls[0]["content"]
        "{'name': 'test'}"
    """
    if not content:
        return []

    results: List[Dict[str, Any]] = []
    search_pos = 0

    while True:
        # Find next start token
        start_idx = content.find(start_token, search_pos)
        if start_idx == -1:
            break

        # Find corresponding end token
        end_idx = content.find(end_token, start_idx + len(start_token))
        if end_idx == -1:
            # No closing token; stop scanning
            break

        # Calculate indices
        content_start = start_idx + len(start_token)
        content_end = end_idx
        full_end = end_idx + len(end_token)

        # Extract text
        inner_content = content[content_start:content_end]
        full_text = content[start_idx:full_end]

        results.append({
            "start_index": start_idx,
            "end_index": full_end,
            "content": inner_content,
            "full_text": full_text
        })

        # Continue search after this match
        search_pos = full_end

    return results


def validate_tool_call_json(content: str) -> bool:
    """
    Check if content is valid JSON that could represent a tool call.

    This is a simple validation utility that checks if the content:
    1. Is valid JSON
    2. Is a dictionary (not a list, string, etc.)
    3. Contains expected tool call fields

    Args:
        content: The content to validate

    Returns:
        bool: True if content appears to be a valid tool call, False otherwise

    Example:
        >>> validate_tool_call_json('{"name": "test", "parameters": {}}')
        True
        >>> validate_tool_call_json('not json')
        False
    """
    if not content or not isinstance(content, str):
        return False

    try:
        # Try to parse as JSON
        data = json.loads(content.strip())

        # Must be a dictionary
        if not isinstance(data, dict):
            return False

        # Should have a name field (common to most tool call formats)
        # This is a lenient check - adjust based on your needs
        if "name" not in data:
            logger.debug(f"Tool call JSON missing 'name' field: {content[:100]}")
            return False

        return True

    except json.JSONDecodeError as e:
        logger.debug(f"Invalid JSON in tool call validation: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error validating tool call JSON: {e}")
        return False

