"""
This module contains default configuration values for the CLAIA application.

It defines default prompts and other default settings.
"""

# External dependencies
import logging

# Internal dependencies
from files import Prompt
from settings import Settings



########################################################################
#                               CONSTANTS                              #
########################################################################
FUNCTION_CALLING_PROMPT = """
You are an AI assistant capable of calling functions. Here are the available functions:

{function_definitions}

When you need to call a function, use the following format:
{function_format}

You can call multiple functions in a single response if needed. Each function call will be replaced with its result.
Incorporate the function call(s) into your response where necessary.
"""



########################################################################
#                             DEFAULT DATA                             #
########################################################################
DEFAULT_PROMPTS = [
  {
    "name": "default",
    "title": "Default Assistant",
    "prompt_text": "You are a helpful assistant, ready to aid the user with any task or question they might have.",
    "description": "A general-purpose assistant for various tasks."
  },
  {
    "name": "poet",
    "title": "Poet",
    "prompt_text": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.",
    "description": "A default assistant with a poetic twist."
  },
  {
    "name": "writer",
    "title": "Writer",
    "prompt_text": "You are a brilliant writer, always adding events and details that give life to the story, making sure to show and not tell about environments, characters, and actions.",
    "description": "An assistant for creative writing tasks."
  },
  {
    "name": "also-writer",
    "title": "Also Writer",
    "prompt_text": "You are a creative writer, skilled in crafting engaging narratives and vivid descriptions. Help the user with their writing tasks, offering suggestions for plot, character development, and prose.",
    "description": "An assistant for creative writing tasks."
  },
  {
    "name": "programmer",
    "title": "Programmer",
    "prompt_text": "You are a skilled programmer, proficient in multiple programming languages. You provide clear explanations and code examples to help with various programming tasks.",
    "description": "An assistant for programming and coding tasks."
  },
  {
    "name": "analyst",
    "title": "Analyst",
    "prompt_text": "You are a data analyst with expertise in statistics and data visualization. You help interpret data, suggest analysis methods, and explain complex analytical concepts.",
    "description": "An assistant for data analysis and interpretation."
  },
  {
    "name": "functions",
    "title": "Function Calling Assistant",
    "prompt_text": FUNCTION_CALLING_PROMPT,
    "description": "An assistant capable of calling functions."
  }
]



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              FUNCTIONS                               #
########################################################################
# Create each of the default prompts if they don't already exist
def initialize_default_prompts(settings: Settings) -> None:
  """
  Initialize default prompts if they don't exist.

  This function checks for each prompt in DEFAULT_PROMPTS, and if it doesn't
  exist, creates it and adds it to the settings.prompt_store list.

  Args:
      settings: The application settings object
  """
  for prompt_data in DEFAULT_PROMPTS:
    # Get the prompt if it exists in the base directory
    prompt = Prompt.load_prompt(prompt_data["name"], settings.files_directory)

    # If the prompt doesn't exist, create it
    if not prompt:
      new_prompt = Prompt.create_prompt(
        base_directory=settings.files_directory,
        prompt_name=prompt_data["name"],
        prompt_text=prompt_data["prompt_text"]
      )

      # If created successfully, add to prompt store
      if new_prompt:
        settings.prompt_store.append(new_prompt)

  return settings