from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    models = client.models.list()
    print(f"Retrieved {len(models.data)} models from OpenRouter")
except Exception as e:
    print(e)
