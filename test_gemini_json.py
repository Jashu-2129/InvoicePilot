import pytest
from llm.client import LLMClient


@pytest.mark.integration
def test_gemini_returns_json():
    prompt = 'Return only valid JSON: {"status": "ok"}'

    response = LLMClient().ask(prompt)

    assert response is not None
    assert response.strip()
