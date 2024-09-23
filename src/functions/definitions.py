import json

functions = [
  {
    "name": "get_current_time",
    "description": "Returns the current time",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The current time in HH:MM:SS format"
    }
  },
  {
    "name": "get_current_date",
    "description": "Returns the current date",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The current date in YYYY-MM-DD format"
    }
  },
  {
    "name": "get_user_name",
    "description": "Returns a hardcoded user name",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The hardcoded user name"
    }
  },
  {
    "name": "greet_user",
    "description": "Greets a user by name",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "The name of the user to greet"
          }
        },
      "required": ["name"]
    },
    "returns": {
      "type": "string",
      "description": "A greeting message"
    }
  }
]

function_format = f"""
[FUNCTION_CALL]{{
"name": "function_name",
"parameters": {{
  "param1": "value1",
  "param2": "value2"
}}
}}[/FUNCTION_CALL]
"""

prompt = f"""
You are an AI assistant capable of calling functions. Here are the available functions:

{json.dumps(functions, indent=2)}

When you need to call a function, use the following format:
{function_format}

Respond to the user's request by calling the appropriate function when necessary.
"""
