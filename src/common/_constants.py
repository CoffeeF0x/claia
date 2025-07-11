########################################################################
#                               MANIFEST                               #
########################################################################
MANIFEST_FILENAME = "manifest.json"



########################################################################
#                             CONVERSATION                             #
########################################################################
DEFAULT_CONVERSATION_TITLE = "New Conversation"

# Default tool format placeholder
DEFAULT_TOOL_FORMAT = """
[TOOL_CALL]{
"name": "tool_name",
"parameters": {
  "param1": "value1",
  "param2": "value2"
}
}[/TOOL_CALL]
"""

# Argument wrapper constants
LEFT_ARG_WRAPPER = "{"
RIGHT_ARG_WRAPPER = "}"