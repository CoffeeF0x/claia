from llama_index.llms.openai import OpenAI

def main(apiKey: str = None) -> None:
  response = OpenAI().complete("What is the meaning of life?")
  print(response)

if __name__ == "__main__":
  main()
