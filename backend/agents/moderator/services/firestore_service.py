import os
import logging
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from google.cloud import storage

logger = logging.getLogger("moderation_pipeline")

# Lazy Global Async Client
_firestore_async_client = None
_storage_client = None

def get_firestore_async_client():
    """Lazily initializes the Firestore Async client to prevent unnecessary overhead."""
    global _firestore_async_client
    if _firestore_async_client is None:
        try:
            # Usamos AsyncClient en lugar de Client, forzando el project literal para evitar fallos de resolución de Vertex
            _firestore_async_client = firestore.AsyncClient(project="ecommerce-police-portfolio", database="firestore-hybrid-shield")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore Async client: {e}")
            raise
    return _firestore_async_client


def get_storage_client():
    """Lazily initializes the Google Cloud Storage client for signing URLs."""
    global _storage_client
    if _storage_client is None:
        try:
            service_account_email = "679252770153-compute@developer.gserviceaccount.com"
            is_local = os.getenv("GOOGLE_CLOUD_PROJECT") is None or os.getenv("LOCAL_DEV") == "true"
            
            if is_local:
                logger.info("Initializing Storage Client for local dev (with impersonated credentials)")
                from google.auth import default
                from google.auth.impersonated_credentials import impersonated_credentials
                
                base_credentials, _ = default()
                credentials = impersonated_credentials.Credentials(
                    source_credentials=base_credentials,
                    target_principal=service_account_email,
                    target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    lifetime=3600
                )
                _storage_client = storage.Client(credentials=credentials)
            else:
                logger.info("Initializing Storage Client for production (native service account)")
                _storage_client = storage.Client()
        except Exception as e:
            logger.error(f"Failed to initialize Storage client: {e}")
            raise
    return _storage_client


def generate_signed_read_url(gcs_uri: str, expiration_days: int = 7) -> str:
    """Generates a v4 signed read URL for a GCS URI (gs://bucket/path)."""
    if not gcs_uri or not gcs_uri.startswith("gs://"):
        return gcs_uri
    try:
        parts = gcs_uri[5:].split("/", 1)
        if len(parts) < 2:
            return gcs_uri
        bucket_name, blob_name = parts[0], parts[1]
        
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=expiration_days),
            method="GET"
        )
        return signed_url
    except Exception as e:
        logger.error(f"Error generating signed read URL for {gcs_uri}: {e}")
        return gcs_uri


async def update_job_status(thread_id: str, status: str, metadata: dict = None):
    """
    Updates the status and metadata of a moderation job in Firestore asynchronously.
    """
    if not thread_id:
        logger.warning("Job status update skipped: thread_id is missing")
        return

    try:
        db = get_firestore_async_client()
        doc_ref = db.collection("jobs").document(thread_id)
        
        payload = {
            "status": status,
            "last_update": datetime.now(timezone.utc)
        }
        
        if metadata:
            payload.update(metadata)
            
        # Detect GCS URIs to generate a valid public HTTPS image_url for the frontend
        gcs_uri = payload.get("image_url") or payload.get("gcs_image_uri") or payload.get("gcs_uri")
        if gcs_uri and gcs_uri.startswith("gs://"):
            try:
                parts = gcs_uri[5:].split("/")
                filename = parts[-1] if parts else "raw_image.jpg"
                public_url = f"https://storage.googleapis.com/ecommerce-police-portfolio-upload/items/{thread_id}/{filename}"
                payload["image_url"] = public_url
            except Exception as e:
                logger.error(f"Failed to generate public GCS URL for payload: {e}")
        
        # Agregamos 'await' porque doc_ref.set en AsyncClient devuelve una corrutina
        await doc_ref.set(payload, merge=True)
        
        logger.info(f"Firestore update successful: phase='{status}', job_id='{thread_id}'")
        
    except Exception as e:
        logger.error(f"Firestore update failed for job_id '{thread_id}': {e}")


async def get_job_status(thread_id: str):
    """
    Retrieves the current status and results of a moderation job from Firestore asynchronously.
    """
    if not thread_id:
        return None

    try:
        db = get_firestore_async_client()
        doc_ref = db.collection("jobs").document(thread_id)
        # Agregamos 'await' para obtener el documento de forma asíncrona
        doc = await doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat()
            return data
        return None
        
    except Exception as e:
        logger.error(f"Failed to fetch job status for job_id '{thread_id}': {e}")
        return None


async def get_auditor_jobs():
    """
    Retrieves a list of pending and historical jobs for the auditor dashboard.
    """
    try:
        db = get_firestore_async_client()
        jobs_ref = db.collection("jobs")
        
        # We fetch all jobs and filter in memory since we don't have complex indexes setup right now.
        # In a real production scenario with many documents, we would use queries like:
        # pending_query = jobs_ref.where("status", "==", "PENDING_HUMAN_REVIEW")
        # However, for this portfolio, fetching and filtering is fine.
        
        docs = await jobs_ref.get()
        
        pending_jobs = []
        historical_jobs = []
        
        for doc in docs:
            data = doc.to_dict()
            data["thread_id"] = doc.id
            
            # Format datetime
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat()
                    
            status = data.get("status")
            if status == "PENDING_HUMAN_REVIEW":
                pending_jobs.append(data)
            elif data.get("human_reviewed") is True:
                historical_jobs.append(data)
                
        # Sort by timestamp (newest first based on last_update)
        pending_jobs.sort(key=lambda x: x.get("last_update", ""), reverse=True)
        historical_jobs.sort(key=lambda x: x.get("last_update", ""), reverse=True)
        
        return {
            "pending": pending_jobs,
            "historical": historical_jobs
        }
    except Exception as e:
        logger.error(f"Failed to fetch auditor jobs: {e}")
        return {"pending": [], "historical": []}


async def get_price_thresholds(category_key: str) -> dict | None:
    """
    Retrieves market price thresholds for a given product category from Firestore asynchronously.
    """
    if not category_key:
        logger.warning("get_price_thresholds called with empty category_key")
        return None

    try:
        db = get_firestore_async_client()
        doc_ref = db.collection("price_thresholds").document(category_key)
        doc = await doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            
            if "min_price" in data and "max_price" in data:
                return {
                    "min_price": int(data["min_price"]),
                    "max_price": int(data["max_price"])
                }
            else:
                logger.warning(
                    f"Price thresholds document for category '{category_key}' "
                    f"is missing required fields (min_price, max_price)"
                )
                return None
        
        logger.info(f"No price thresholds found for category '{category_key}'")
        return None
        
    except Exception as e:
        logger.error(
            f"Failed to fetch price thresholds for category '{category_key}': {e}"
        )
        return None


async def update_ui_state(thread_id: str, current_node: str, ui_context: str, ui_message: str, status: str = "PROCESSING", result: dict = None, additional_metrics: dict = None):
    """
    Updates the UI Projection (View Model) in Firestore asynchronously.
    Fire-and-forget to avoid blocking the LangGraph execution.
    """
    if not thread_id:
        logger.warning("UI Projection update skipped: thread_id is missing")
        return
        
    try:
        db = get_firestore_async_client()
        # Escibimos en una colección separada o en jobs? El prompt dice "escribiéndolo en Firestore mediante un modelo de View Model". 
        # Lo más limpio es una colección dedicada "ui_projections".
        doc_ref = db.collection("ui_projections").document(thread_id)
        
        payload = {
            "status": status,
            "current_node": current_node,
            "ui_context": ui_context,
            "ui_message": ui_message,
            "updated_at": firestore.SERVER_TIMESTAMP
        }
        
        if result is not None:
            payload["result"] = result
            
        if additional_metrics:
            payload.update(additional_metrics)
            
        try:
            # Obligatorio usar update() y nunca set() a menos que sea creación
            await doc_ref.update(payload)
        except Exception as e:
            from google.api_core.exceptions import NotFound
            if isinstance(e, NotFound):
                # Si no existe (creación inicial), usamos set()
                # Nos aseguramos de tener el result en null como pide el prompt
                if "result" not in payload:
                    payload["result"] = None
                await doc_ref.set(payload)
            else:
                logger.error(f"Firestore UI projection update() failed for '{thread_id}': {e}")
                
    except Exception as e:
        # Maneja las excepciones para que un error en el logeo nunca detenga al agente
        logger.error(f"Failed to process UI projection for '{thread_id}': {e}")