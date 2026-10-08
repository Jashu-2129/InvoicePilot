import os
from dotenv import load_dotenv
from google import genai

load_dotenv()


class LLMClient:
    """Simple wrapper around the Google Gemini API."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gemini-3.8-flash")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Please add it to your .env file."
            )

        self.client = genai.Client(api_key=self.api_key)

    def ask(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the text response."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return response.text