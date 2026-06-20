import os
import json
import logging
import functions_framework
from google.cloud import storage
from vertexai.preview import reasoning_engines


# Configuración del logger para producción
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Inicialización global
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")


if project_id:
    from vertexai import init as vertexai_init
    vertexai_init(project=project_id, location=region)


storage_client = storage.Client()


@functions_framework.cloud_event
def process_image_event(cloud_event):
    data = cloud_event.data
    file_name = data["name"]
    bucket_name = data["bucket"]

    # 1. FILTRO DE RUTA ESTRICTO
    if not (file_name.startswith("triggers/") and file_name.endswith("metadata.json")):
        logger.info(f"Archivo omitido por ruta o extensión: {file_name}")
        return

    logger.info(f"Iniciando procesamiento del evento para: {file_name}")

    try:
        # 2. LECTURA DEL METADATA
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        json_data = json.loads(blob.download_as_string())

        gcs_image_uri = json_data.get("gcs_image_uri")
        path_parts = file_name.split("/")
        job_id = path_parts[1] if len(path_parts) > 1 else json_data.get("job_id", "unknown")

        if not gcs_image_uri:
            logger.error(f"Estructura inválida en {file_name}: falta gcs_image_uri")
            return

        # 3. OPTIMIZACIÓN DE IMAGEN
        try:
            from shared.image_utils import optimize_image
        except ImportError:
            import sys
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
            from shared.image_utils import optimize_image

        uri_clean = gcs_image_uri.replace("gs://", "").split("/", 1)
        source_bucket = storage_client.bucket(uri_clean[0])
        source_blob = source_bucket.blob(uri_clean[1])

        logger.info(f"Descargando imagen original para optimizar: {gcs_image_uri}")
        image_bytes = source_blob.download_as_bytes()
        optimized_bytes = optimize_image(image_bytes)

        optimized_blob_name = f"items/{job_id}/optimized_image.webp"
        optimized_blob = bucket.blob(optimized_blob_name)
        optimized_blob.upload_from_string(optimized_bytes, content_type="image/webp")

        optimized_gcs_uri = f"gs://{bucket_name}/{optimized_blob_name}"
        logger.info(f"Imagen optimizada almacenada con éxito en: {optimized_gcs_uri}")

        # 4. INVOCACIÓN AL REASONING ENGINE (GRAFO)
        reasoning_engine_id = os.getenv("REASONING_ENGINE_ID")
        if not reasoning_engine_id:
            logger.error("Llamada abortada: REASONING_ENGINE_ID no está configurado")
            return

        logger.info(f"Enviando payload al Reasoning Engine ID: {reasoning_engine_id}")
        engine = reasoning_engines.ReasoningEngine(reasoning_engine_id)

        # Construimos el diccionario con las llaves exactas que busca tu agente
        agent_payload = {
            "title": json_data.get("title", ""),
            "description": json_data.get("description", ""),
            "price": json_data.get("price", 0),
            "gcs_uri": optimized_gcs_uri,  # Tu agente busca 'gcs_uri'
            "thread_id": job_id            # Tu agente busca 'thread_id' para el checkpointer
        }

        # Invocamos usando 'input_data' como argumento de palabra clave (kwarg)
        response = engine.query(input_data=agent_payload)
        
        logger.info(f"Grafo ejecutado con éxito para job_id {job_id}. Respuesta: {response}")
        
    except Exception as e:
        # exc_info=True adjunta automáticamente todo el Traceback del error
        # convirtiéndolo en un log de severidad ERROR/CRITICAL real en GCP
        logger.critical(f"Falla crítica en el pipeline de ejecución: {str(e)}", exc_info=True)