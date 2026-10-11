import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

try:
    models = client.models.list()
    print("\n--- Available Groq Models for your API Key ---")
    for model in models.data:
        print(f" - {model.id}")
    print("----------------------------------------------\n")
except Exception as e:
    print(f"Error fetching models: {e}")