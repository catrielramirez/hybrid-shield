import re

def clean_json_string(raw_text: str) -> str:
    """Elimina bloques de Markdown y caracteres de control ASCII que rompen json.loads."""
    if not raw_text:
        return "{}"
    # Quita los tags de bloque de código markdown si existen
    clean = re.sub(r"```json|```", "", raw_text).strip()
    # Elimina caracteres de control (0-31) y otros no imprimibles que causan el error
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", clean)
    return clean
