# External dependencies
import json
import torch
from typing import Dict, Any

# Internal dependencies
from commands.base import Command
from errors import Result
from settings import Settings



##################################################
#                 COMMAND CLASS                  #
##################################################
class ModuleCommands(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    if len(commands) > 1:
      if commands[1] == "test":
        test()
      elif commands[1] == "mini":
        minitest()
      elif commands[1] == "function":
        test_function_calling(settings)
      else:
        self.help()
    else:
      self.help()

    return result

  def help(self) -> None:
    """Display help information for experimental commands."""
    print("Experimental Commands:")
    print("  experimental test       - Test Stable Diffusion")
    print("  experimental mini       - Test MiniCPM3 model")
    print("  experimental function   - Test function calling capabilities")



##################################################
#                   FUNCTIONS                    #
##################################################
def test():
  """
  Test function for Stable Diffusion.
  """
  from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

  model_id = "stabilityai/stable-diffusion-2-1"

  # Use the DPMSolverMultistepScheduler (DPM-Solver++) scheduler here instead
  pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
  pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
  pipe = pipe.to("cuda")

  prompt = "a photo of an astronaut riding a horse on mars"
  image = pipe(prompt).images[0]

  image.save("files/astronaut_rides_horse.png")

def minitest():
  """
  Test function for MiniCPM3 model.
  """
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
  print(responses)

def test_function_calling(settings: Settings):
  """
  Test function for function calling capabilities.

  Args:
    settings: The Claia settings
  """
  from models import run as model_run

  # Prepare system message with function definitions
  system_message = f"""You are an AI assistant capable of calling functions. Here are the available functions:

{json.dumps(FUNCTION_DEFINITIONS, indent=2)}

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

  # Run tests
  for prompt in test_prompts:
    print(f"\nUser: {prompt}")
    messages = [
      {"role": "system", "content": system_message},
      {"role": "user", "content": prompt}
    ]
    result = model_run(settings.active_model, messages, settings=settings)

    if result.is_error():
      print(f"Error: {result.get_message()}")
    else:
      response = result.data
      print(f"AI: {response}")

      # Check for function calls
      if "[FUNCTION_CALL]" in response:
        start = response.index("[FUNCTION_CALL]") + len("[FUNCTION_CALL]")
        end = response.index("[/FUNCTION_CALL]")
        function_call = json.loads(response[start:end])

        # Execute the function
        if function_call["name"] == "get_current_time":
          result = get_current_time()
        elif function_call["name"] == "get_current_date":
          result = get_current_date()
        elif function_call["name"] == "get_user_name":
          result = get_user_name()
        elif function_call["name"] == "greet_user":
          result = greet_user(function_call["parameters"]["name"])
        else:
          result = "Unknown function"

        print(f"Function result: {result}")

  print("\nFunction calling test completed.")



def sample_function(params: Dict[str, Any]) -> Dict[str, Any]:
  """
  A sample function that demonstrates how to create a module function.

  Args:
    params: Function parameters

  Returns:
    Dict[str, Any]: Function result
  """
  return {
    "success": True,
    "message": "Sample function executed successfully!",
    "data": params
  }

FUNCTION_DEFINITIONS = [
  {
    "name": "sample_function",
    "description": "A sample function that demonstrates module functionality",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "Text to process"
        }
      },
      "required": ["text"]
    }
  }
]