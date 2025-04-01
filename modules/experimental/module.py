"""
Experimental module for CLAI application.

This module provides experimental features and testing capabilities.
"""

# External dependencies
import json
import torch
from typing import Dict, Any
import logging

# Internal dependencies
from commands.base import Command, command
from results import Result
from settings import Settings



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class ModuleCommands(Command):
  """Command class for experimental features and testing."""

  @command(
    path=["test"],
    description="Test Stable Diffusion model",
    help_text="Run a test of the Stable Diffusion model",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Result of the Stable Diffusion test"
    },
    ai_callable=True
  )
  def test_stable_diffusion(self, settings: Settings) -> str:
    """
    Test function for Stable Diffusion.

    Args:
      settings: Application settings

    Returns:
      str: Result message
    """
    try:
      from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

      model_id = "stabilityai/stable-diffusion-2-1"

      # Use the DPMSolverMultistepScheduler (DPM-Solver++) scheduler here instead
      pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
      pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
      pipe = pipe.to("cuda")

      prompt = "a photo of an astronaut riding a horse on mars"
      image = pipe(prompt).images[0]

      image.save("files/astronaut_rides_horse.png")
      return "Stable Diffusion test completed successfully. Image saved to files/astronaut_rides_horse.png"
    except Exception as e:
      return f"Error running Stable Diffusion test: {str(e)}"

  @command(
    path=["mini"],
    description="Test MiniCPM3 model",
    help_text="Run a test of the MiniCPM3 model",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Result of the MiniCPM3 test"
    },
    ai_callable=True
  )
  def test_minicpm(self, settings: Settings) -> str:
    """
    Test function for MiniCPM3 model.

    Args:
      settings: Application settings

    Returns:
      str: Result message
    """
    try:
      from transformers import AutoModelForCausalLM, AutoTokenizer

      path = "openbmb/MiniCPM3-4B"
      device = "cuda"

      tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
      model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16, device_map=device, trust_remote_code=True)

      messages = [
        {"role": "user", "content": "Hey bro, what's up?"},
      ]
      model_inputs = tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(device)

      model_outputs = model.generate(
        model_inputs,
        max_new_tokens=1024,
        top_p=0.7,
        temperature=0.7
      )

      output_token_ids = [
        model_outputs[i][len(model_inputs[i]):] for i in range(len(model_inputs))
      ]

      responses = tokenizer.batch_decode(output_token_ids, skip_special_tokens=True)[0]
      return f"MiniCPM3 test completed successfully. Response: {responses}"
    except Exception as e:
      return f"Error running MiniCPM3 test: {str(e)}"

  @command(
    path=["function"],
    description="Test function calling capabilities",
    help_text="Run a test of the function calling capabilities",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Result of the function calling test"
    },
    ai_callable=True
  )
  def test_function_calling(self, settings: Settings) -> str:
    """
    Test function for function calling capabilities.

    Args:
      settings: The Claia settings

    Returns:
      str: Result message
    """
    try:
      from models import run as model_run

      # Define function definitions for testing
      function_definitions = [
        {
          "name": "get_current_time",
          "description": "Returns the current time",
          "parameters": {
            "type": "object",
            "properties": {}
          }
        },
        {
          "name": "get_current_date",
          "description": "Returns the current date",
          "parameters": {
            "type": "object",
            "properties": {}
          }
        },
        {
          "name": "get_user_name",
          "description": "Returns the user name",
          "parameters": {
            "type": "object",
            "properties": {}
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
          }
        }
      ]

      # Prepare system message with function definitions
      system_message = f"""You are an AI assistant capable of calling functions. Here are the available functions:

{json.dumps(function_definitions, indent=2)}

When you need to call a function, use the following format:
[FUNCTION_CALL]{{
"name": "function_name",
"parameters": {{
  "param1": "value1",
  "param2": "value2"
}}
}}[/FUNCTION_CALL]

Respond to the user's request by calling the appropriate function when necessary."""

      # Test prompts
      test_prompts = [
        "What time is it?",
        "Can you tell me today's date?",
        "What's my name?",
        "Please greet me!",
        "What's the current time and date?"
      ]

      results = []

      # Run tests
      for prompt in test_prompts:
        results.append(f"\nUser: {prompt}")
        messages = [
          {"role": "system", "content": system_message},
          {"role": "user", "content": prompt}
        ]
        result = model_run(settings.active_model, messages, settings=settings)

        if result.is_error():
          results.append(f"Error: {result.get_message()}")
        else:
          response = result.data
          results.append(f"AI: {response}")

          # Check for function calls
          if "[FUNCTION_CALL]" in response:
            start = response.index("[FUNCTION_CALL]") + len("[FUNCTION_CALL]")
            end = response.index("[/FUNCTION_CALL]")
            function_call = json.loads(response[start:end])
            results.append(f"Function call detected: {function_call['name']}")

      results.append("\nFunction calling test completed.")
      return "\n".join(results)
    except Exception as e:
      return f"Error running function calling test: {str(e)}"

  @command(
    path=["sample"],
    description="A sample function that demonstrates module functionality",
    help_text="Execute a sample function with the provided text",
    parameters={
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "Text to process"
        }
      },
      "required": ["text"]
    },
    returns={
      "type": "object",
      "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "data": {"type": "object"}
      }
    },
    ai_callable=True
  )
  def sample_function(self, settings: Settings, text: str) -> Dict[str, Any]:
    """
    A sample function that demonstrates how to create a module function.

    Args:
      settings: Application settings
      text: Text to process

    Returns:
      Dict[str, Any]: Function result
    """
    return {
      "success": True,
      "message": "Sample function executed successfully!",
      "data": {"text": text}
    }