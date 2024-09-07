from anthropic import Anthropic

client = None

def main(apiKey, messages):
  global client
  response = None
  message = None

  if client is None:
    client = Anthropic(api_key=apiKey)

  message = client.messages.create(
      model="claude-3-5-sonnet-20240620",
      max_tokens=1024,
      messages=[
          {"role": "user", "content": "Hello, Claude"}
      ]
  )

  response = message.content

  return str(response)
