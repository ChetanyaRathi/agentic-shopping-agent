"""Color vision fallback for unknown product colors."""
import base64

from google.genai import types

from shopping_agent.llm import _client as client
from shopping_agent.cost.accounting import METER

VISION_MODEL = "gemini-2.5-flash"


def confirm_color_vision(image_data: str, mime_type: str, desired_color: str) -> bool:
    """Ask Gemini Vision if the main product in the image matches the desired color."""
    prompt = f"Is the main product in this image {desired_color}? Answer strictly 'yes' or 'no'."
    
    # decode base64 data to pass bytes
    image_bytes = base64.b64decode(image_data)
    
    try:
        resp = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ],
        )
        if resp.usage_metadata:
            METER.record(VISION_MODEL, resp.usage_metadata.prompt_token_count, resp.usage_metadata.candidates_token_count)
            
        answer = resp.text.strip().lower()
        return "yes" in answer
    except Exception:
        return False
