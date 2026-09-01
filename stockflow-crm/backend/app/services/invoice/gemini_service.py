import json
import re

from google import genai
from google.genai import types

from app.core.config import settings

_client = genai.Client(api_key=settings.GOOGLE_API_KEY)

_PROMPT = """
Sos un asistente de extracción de datos de facturas de proveedores.

PASO 1 — CLASIFICAR. Antes de extraer nada, determiná si el documento es
realmente una factura, un remito o un comprobante de compra con líneas de
productos. Fotografías de personas, animales, paisajes, capturas de pantalla,
documentos de identidad, recetas y cualquier otro contenido NO son facturas.

Si NO es una factura:
  - devolvé "is_invoice": false
  - describí en "document_type" qué es realmente el archivo, en español y en
    pocas palabras (por ejemplo "fotografía de un gato", "captura de pantalla")
  - dejá "items" como una lista vacía
  - NO inventes ni estimes productos bajo ninguna circunstancia

PASO 2 — EXTRAER. Solo si es una factura, extraé sus líneas.

Devolvé ÚNICAMENTE un objeto JSON, sin markdown, sin explicaciones y sin
bloques de código.

Esquema requerido:
{
  "is_invoice": <true | false>,
  "document_type": "<qué es el documento, en español>",
  "supplier": "<nombre del proveedor tal como figura, o null>",
  "date": "<fecha de la factura en formato YYYY-MM-DD, o null>",
  "items": [
    {
      "description": "<descripción del producto o servicio>",
      "quantity": <número>,
      "unit_price": <número>,
      "confidence": "<high | medium | low>"
    }
  ]
}

Reglas de confianza:
- "high"   → el valor se lee con claridad
- "medium" → el valor se dedujo o se lee parcialmente
- "low"    → el valor se estimó o es muy poco claro

Reglas adicionales:
- quantity y unit_price siempre tienen que ser números, nunca null ni texto.
- Si un valor es ilegible, usá tu mejor estimación numérica y poné confidence "low".
- Extraé TODAS las líneas por separado: no las agrupes ni las resumas.
- Ignorá subtotales, impuestos, envío y descuentos, salvo que sean productos.
"""

# MIME types aceptados por el endpoint.
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Firmas binarias reales de cada formato. Se comprueban porque el content_type
# lo declara el cliente y puede no corresponderse con el contenido del archivo.
_FIRMAS: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


def contenido_coincide_con_tipo(file_bytes: bytes, mime_type: str) -> bool:
    """
    Comprueba que el contenido del archivo se corresponda con el tipo declarado.

    Evita que se procese un archivo con la extensión cambiada: el navegador
    envía el ``content_type`` sin verificarlo.
    """
    if not file_bytes:
        return False

    if mime_type == "image/webp":
        return file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP"

    firmas = _FIRMAS.get(mime_type)
    if not firmas:
        return False
    return any(file_bytes.startswith(firma) for firma in firmas)


def process_invoice_file(file_bytes: bytes, mime_type: str) -> dict:
    """
    Envía el archivo a Gemini y devuelve el diccionario ya parseado.

    Lanza ``ValueError`` si la respuesta no es JSON válido.
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

    text = (response.text or "").strip()

    # Se quitan las vallas de markdown por si el modelo ignora response_mime_type.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini devolvió contenido que no es JSON: {text[:200]}") from exc

    if not isinstance(data, dict):
        raise ValueError("Gemini devolvió una estructura inesperada.")
    return data
