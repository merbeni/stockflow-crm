import json
import re

from google import genai
from google.genai import types

from app.core.config import settings

_client = genai.Client(api_key=settings.GOOGLE_API_KEY)

_PROMPT = """
You are an invoice data extraction assistant.
Analyze the provided invoice document and return ONLY a JSON object — no markdown,
no explanation, no code fences.

Required schema:
{
  "supplier": "<supplier name as it appears on the invoice, or null>",
  "date": "<invoice date as YYYY-MM-DD, or null>",
  "items": [
    {
      "description": "<product or service description>",
      "quantity": <number>,
      "unit_price": <number>,
      "confidence": "<high | medium | low>"
    }
  ]
}

Confidence rules:
- "high"   → value is clearly readable
- "medium" → value was inferred or partially readable
- "low"    → value was estimated or is very unclear

Additional rules:
- quantity and unit_price must always be numbers, never null or strings.
- If a value is unreadable, use your best numeric estimate and set confidence to "low".
- Extract ALL line items individually — do not group or summarize.
- Ignore subtotals, taxes, shipping, and discount lines unless they are products.
"""

# MIME types accepted by this endpoint
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def process_invoice_file(file_bytes: bytes, mime_type: str) -> dict:
    """
    Send the invoice file to Gemini and return the parsed dict.
    Raises ValueError if the response is not valid JSON.
    """
    response = _client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            types.Part.from_text(text=_PROMPT),
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    text = response.text.strip()

    # Strip markdown code fences in case the model ignores response_mime_type.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned non-JSON content: {text[:200]}") from exc
