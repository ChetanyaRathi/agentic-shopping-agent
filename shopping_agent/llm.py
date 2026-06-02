"""Gemini client and a structured-output helper."""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from shopping_agent.cost.accounting import METER

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

FLASH_LITE = "gemini-2.5-flash-lite"   # cheapest tier
FLASH = "gemini-2.5-flash"             # escalation tier


def _call_and_record(prompt: str, schema: type[BaseModel], model: str) -> BaseModel | None:
    resp = _client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    if resp.usage_metadata:
        METER.record(model, resp.usage_metadata.prompt_token_count, resp.usage_metadata.candidates_token_count)
    return resp.parsed


def generate_structured(prompt: str, schema: type[BaseModel], model: str = FLASH_LITE) -> BaseModel:
    """Ask Gemini for JSON matching `schema`, returned as a parsed model instance. Escalates on failure."""
    try:
        parsed = _call_and_record(prompt, schema, model)
        if parsed is not None:
            return parsed
    except Exception:
        pass
    
    # Escalation to more capable model if it failed or returned None
    return _call_and_record(prompt, schema, FLASH)
