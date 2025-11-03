"""
This module contains default configuration values for the CLAIA application.

It defines default prompts and other default settings.
"""

# External dependencies
import logging

# Internal dependencies
from claia.lib.data import Prompt, FileSystemRepository
from .settings import Settings



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

  This function loads existing prompts from disk and adds them to the
  settings.prompt_store list. It only creates new prompts for defaults
  that don't already exist.

  Args:
      settings: The application settings object
  """
  logger.info("Initializing default prompts")

  # Create file repository for managing prompts
  file_repo = FileSystemRepository(settings.files_directory)

  # Load existing prompts from repository
  existing_prompts_metadata = file_repo.list_all(file_type='prompts')
  existing_prompt_names = {metadata.get('prompt_name') for metadata in existing_prompts_metadata}
  
  logger.debug(f"Found {len(existing_prompts_metadata)} existing prompts")
  
  # Load existing prompts and add to prompt store
  for metadata in existing_prompts_metadata:
    try:
      prompt_id = metadata.get('id')
      existing_prompt = file_repo.load(prompt_id, load_content=True)
      if existing_prompt:
        settings.prompt_store.append(existing_prompt)
        logger.debug(f"Loaded existing prompt '{existing_prompt.prompt_name}' (ID: {existing_prompt.id})")
    except Exception as e:
      logger.error(f"Failed to load existing prompt {prompt_id}: {e}")

  # Create prompt objects from defaults that don't exist yet
  for prompt_data in DEFAULT_PROMPTS:
    prompt_name = prompt_data["name"]
    validated_name = Prompt.validate_prompt_name(prompt_name)
    
    # Skip if prompt already exists
    if validated_name in existing_prompt_names:
      logger.debug(f"Prompt '{prompt_name}' already exists, skipping creation")
      continue
    
    logger.debug(f"Creating new prompt '{prompt_name}'")
    
    try:
      # Create the prompt with content using the repository pattern
      new_prompt = Prompt.from_content(
        content=prompt_data["prompt_text"],
        prompt_name=validated_name,
        prompt_type="text"
      )
      
      # Save to repository (repository handles directory creation and file management)
      file_repo.save(new_prompt)
      
      # Add to prompt store for in-memory access
      settings.prompt_store.append(new_prompt)
      
      logger.debug(f"Successfully created prompt '{prompt_name}' (ID: {new_prompt.id})")
      
    except Exception as e:
      logger.error(f"Failed to create prompt '{prompt_name}': {e}")

  return settings

def initialize_default_model(settings: Settings) -> None:
  """
  Initialize the default model if it doesn't exist.
  """
  logger.info("Initializing default model")

  if settings.default_model:
    logger.debug(f"Setting active model to default: {settings.default_model}")
    settings.active_model = settings.default_model

  return settings



########################################################################
#                         INITIALIZE DEFAULTS                          #
########################################################################
def initialize_defaults(settings: Settings) -> None:
  """
  This function is a central function to initialize the defaults
  """
  logger.info("Initializing defaults")

  settings = initialize_default_prompts(settings)
  settings = initialize_default_model(settings)

  return settings
