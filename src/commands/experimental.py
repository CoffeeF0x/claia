import help

from commands.base import Command
from errors import Result
from settings import Settings



##################################################
#                 COMMAND CLASS                  #
##################################################
class ExperimentalCommand(Command):
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
        help.unrecognizedCommand()
    else:
      help.experimentalCommands()

    return result



##################################################
#                   FUNCTIONS                    #
##################################################
def test():
  import torch
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
  from transformers import AutoModelForCausalLM, AutoTokenizer
  import torch

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
  from models.registry import run as model_run
  from errors import Result
  import json

  # Define sample functions
  def get_current_time():
    import datetime
    return datetime.datetime.now().strftime("%H:%M:%S")

  def get_current_date():
    import datetime
    return datetime.date.today().strftime("%Y-%m-%d")

  def get_user_name():
    return "John Doe"

  def greet_user(name):
    return f"Hello, {name}!"

  # Define function list
  function_list = [
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

  # Prepare system message with function definitions
  system_message = f"""You are an AI assistant capable of calling functions. Here are the available functions:

{json.dumps(function_list, indent=2)}

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
