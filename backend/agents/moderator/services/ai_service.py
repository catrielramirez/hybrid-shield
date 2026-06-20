import os
import logging
import json
import urllib.parse
import asyncio
from typing import Optional
from google import genai
from google.genai import types
from google.cloud import storage
from ..utils.prompt_loader import load_prompt
from ..schemas import MultimodalProductFeatures, SafetyAnalysis

# Configuración de Logging
logger = logging.getLogger("moderation_pipeline")

# 1. Configuración Global (Instancias únicas para eficiencia)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# 1. Patrón Lazy Loading para Clientes
_genai_client = None
_storage_client = None

def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    return _genai_client

def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client

# Caché en memoria para evitar llamadas redundantes a GCS
_uri_resolution_cache = {}


# ================================================================
# Interfaz del Modelo
# ================================================================

class GenAIModelInterface:
    """
    Abstracción que expone una interfaz limpia a los nodos.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, contents: list | str, response_mime_type: str = "application/json") -> types.GenerateContentResponse:
        config = types.GenerateContentConfig(response_mime_type=response_mime_type)
        return get_genai_client().models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )

    async def generate_async(
        self, 
        contents: list | str, 
        response_schema: Optional[type] = None,
        response_mime_type: str = "application/json"
    ) -> types.GenerateContentResponse:
        config = types.GenerateContentConfig(
            response_mime_type=response_mime_type,
            response_schema=response_schema,
            temperature=0.0 if response_schema else None,
            thinking_config=types.ThinkingConfig(thinking_budget=0) if response_schema is not None else None
        )
        return await get_genai_client().aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )


# ================================================================
# Funciones Utilitarias
# ================================================================

async def resolve_gcs_uri(gcs_uri: str) -> str:
    """
    Verifica si el archivo existe en GCS de forma no bloqueante. Si no, prueba extensiones 
    alternativas (.jpg, .png, .jpeg). Usa caché para optimizar.
    """
    # 1. Retornar inmediatamente si ya resolvimos esta URI anteriormente
    if gcs_uri in _uri_resolution_cache:
        return _uri_resolution_cache[gcs_uri]

    if not gcs_uri.startswith("gs://"):
        return gcs_uri

    # Parsear gs://bucket/path/to/file.jpg
    parts = gcs_uri[5:].split("/", 1)
    if len(parts) < 2:
        return gcs_uri
    
    bucket_name, blob_path = parts
    bucket = get_storage_client().bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # 2. Verificación si el original existe de manera asíncrona delegada
    exists = await asyncio.to_thread(blob.exists)
    if exists:
        _uri_resolution_cache[gcs_uri] = gcs_uri
        return gcs_uri

    # 3. Intentar variantes si falla
    base_path = blob_path.rsplit('.', 1)[0]
    alternatives = [f"{base_path}.jpg", f"{base_path}.png", f"{base_path}.jpeg"]

    for alt_name in alternatives:
        if alt_name == blob_path:
            continue
        
        alt_blob = bucket.blob(alt_name)
        alt_exists = await asyncio.to_thread(alt_blob.exists)
        if alt_exists:
            new_uri = f"gs://{bucket_name}/{alt_name}"
            logger.info(f"Ruta corregida: {gcs_uri} -> {new_uri}")
            _uri_resolution_cache[gcs_uri] = new_uri
            return new_uri
            
    # Si nada funciona, guardamos el original (fallido) para no reintentar
    _uri_resolution_cache[gcs_uri] = gcs_uri
    return gcs_uri


def get_gemini_model(model_name: str = "gemini-2.5-flash-lite") -> GenAIModelInterface:
    try:
        return GenAIModelInterface(model_name)
    except Exception as e:
        logger.error(f"Error al configurar la interfaz del modelo {model_name}: {e}")
        raise


def _get_mime_type(gcs_uri: str) -> str:
    ext = gcs_uri.lower().split("?")[0].rsplit(".", 1)[-1]
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext, "image/jpeg")


def _encode_gcs_uri(gcs_uri: str) -> str:
    if gcs_uri.startswith("gs://"):
        prefix = "gs://"
        path = gcs_uri[len(prefix):]
        encoded_path = urllib.parse.quote(path, safe="/")
        return prefix + encoded_path
    return gcs_uri


# ================================================================
# Servicios de IA (Análisis y Extracción)
# ================================================================

async def analyze_safety(title: str, description: str, model_name: str = "gemini-2.5-flash-lite") -> dict:
    raw_prompt = load_prompt("analyze_safety_prompt")
    prompt = raw_prompt.format(title=title, description=description)
    
    try:
        model = get_gemini_model(model_name)
        response = await model.generate_async(contents=prompt, response_schema=SafetyAnalysis)
        response_text = getattr(response, "text", "") or ""
        if not response_text.strip():
            logger.warning("Empty response received from Gemini for safety analysis.")
            data = {"error": "empty_response", "status": "error"}
        else:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSONDecodeError: {json_err} - Raw response: {response_text}")
                data = {"error": "invalid_json", "status": "error"}
        
        usage_metadata = getattr(response, "usage_metadata", None)
        usage = {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata else 0,
            "candidates_tokens": getattr(usage_metadata, "candidates_token_count", 0) if usage_metadata else 0,
            "model_name": model_name
        }
        return {"data": data, "usage": usage}
        
    except Exception as e:
        logger.error(f"Safety analysis failed: {e}")
        return {
            "data": {"is_critical": None, "reason": "API Error", "status": "error", "error_details": str(e)},
            "usage": {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": model_name}
        }


async def extract_multimodal_features(gcs_uri: str, product_data: dict, model_name: str = "gemini-2.5-flash-lite") -> dict:
    raw_prompt = load_prompt("extract_multimodal_features_prompt")
    
    prompt = raw_prompt.format(
        title=product_data.get('title', 'N/A'),
        description=product_data.get('description', 'N/A'),
        price=product_data.get('price', 'N/A')
    )
    
    try:
        # Resolver URI y usar caché (ahora de forma no bloqueante)
        resolved_uri = await resolve_gcs_uri(gcs_uri)
        
        safe_uri = _encode_gcs_uri(resolved_uri)
        mime_type = _get_mime_type(resolved_uri)
        image_part = types.Part.from_uri(file_uri=safe_uri, mime_type=mime_type)
        
        model = get_gemini_model(model_name)
        
        response = await model.generate_async(
            contents=[image_part, prompt], 
            response_schema=MultimodalProductFeatures
        )
        
        response_text = getattr(response, "text", "") or ""
        if not response_text.strip():
            logger.warning("Empty response received from Gemini for multimodal extraction.")
            data = {"error": "empty_response", "status": "error"}
        else:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSONDecodeError: {json_err} - Raw response: {response_text}")
                data = {"error": "invalid_json", "status": "error", "raw_content": response_text}

        
        usage_metadata = getattr(response, "usage_metadata", None)
        usage = {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata else 0,
            "candidates_tokens": getattr(usage_metadata, "candidates_token_count", 0) if usage_metadata else 0,
            "model_name": model_name
        }
        return {"data": data, "usage": usage}

    except Exception as e:
        logger.error(f"Multimodal extraction failed for {gcs_uri}: {e}")
        return {
            "data": {"is_sellable": None, "status": "error", "error_details": str(e), "error": "multimodal_analysis_failed"},
            "usage": {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": model_name}
        }