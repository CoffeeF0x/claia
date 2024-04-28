from openai import OpenAI

def openaiCompletionCall(messages, apiKey, baseUrl=""):
  result = ""

  if (baseUrl):
    client = OpenAI(
      api_key=apiKey,
      base_url=baseUrl
    )
  else:
    client = OpenAI(
      api_key=apiKey
    )

  try:
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=messages
    )

    result = completion
    print(completion.choices[0].message.content)

  except Exception as e:
    result = "API Tools Error"
    print(f"An unexpected error occurred: {e}")

  return result
