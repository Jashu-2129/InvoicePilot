import os
from dotenv import load_dotenv

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

        try:
            from google import genai
        except ImportError as exc:
            raise ImportError(
                "The Google Gemini SDK is missing. Install project dependencies "
                "with: python -m pip install -r requirements.txt"
            ) from exc

        self.client = genai.Client(api_key=self.api_key)

    def ask(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the text response."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        text = response.text

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "Gemini returned an empty text response."
                "Try again or check the model response."
            )

        return text.strip()