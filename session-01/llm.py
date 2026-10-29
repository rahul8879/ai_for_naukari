from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

open_ai_api_key = os.getenv("api_test")

client = OpenAI()

response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {
      "role": "user",
      "content": "Hello, who won the world series in 2020?"
    }
  ]
)



print(response.choices[0].message.content)
