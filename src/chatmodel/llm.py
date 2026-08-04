
import os
from openai import OpenAI
from src.config.settings import settings


# Initialize the client (automatically uses OPENAI_API_KEY environment variable)
if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in environment variables.")

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def test_openai_api(prompt: str):
    """
    Test the OpenAI API integration by sending a simple chat completion request.
    Ensure that the OPENAI_API_KEY is set in the environment variables.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Fast and cost-effective model
        messages=[
            {"role": "system", "content": "You are a helpful AI recommendation assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )

    print(response.choices[0].message.content)

    return response.choices[0].message.content.strip()