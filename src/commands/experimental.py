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