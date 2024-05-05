from llama_index.llms.openai import OpenAI
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import ChatMemoryBuffer
# from llama_index.core.schema import BaseComponent
from settings import Settings

def main(settings: Settings) -> None:
  quit = False
  # messages: list[ChatMessage] = []
  # memory = ChatMemoryBuffer()
  functions = {
    "multiply": FunctionTool.from_defaults(fn=multiply),
    "add": FunctionTool.from_defaults(fn=add)
  }
  llm = OpenAI(model="gpt-3.5-turbo", api_key=settings.openAiApiToken)
  agent = OpenAIAgent.from_tools(
    [functions["multiply"], functions["add"]],
    llm=llm,
    # max_function_calls=3,
    # memory=memory,
    # message_history=messages,
    verbose=True
  )

  while not quit:
    user_input = input("Enter your input or 'q' to exit: ")
    if user_input == "q":
      quit = True
    else:
      response = agent.chat(user_input)
      print(str(response))

def multiply(a: int, b: int) -> int:
    """Multiple two integers and returns the result integer"""
    return a * b

def add(a: int, b: int) -> int:
    """Add two integers and returns the result integer"""
    return a + b

if __name__ == "__main__":
  main()
