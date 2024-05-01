import openai

def streamingTest():
  print("AI Streaming Test. Go!")

  response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    messages=[
      {'role': 'user', 'content': "What's 1+1? Answer in one word."}
    ],
    temperature=0,
    stream=True  # this time, we set stream=True
  )

  for chunk in response:
    print(chunk)
    print(chunk.choices[0].delta.content)
    print("****************")

# "role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."
