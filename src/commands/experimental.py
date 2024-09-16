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
