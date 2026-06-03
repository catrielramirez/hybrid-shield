import logging
from datetime import datetime, timezone
from google.cloud import firestore

logger = logging.getLogger("moderation_pipeline")

# Lazy Global Async Client
_firestore_async_client = None

def get_firestore_async_client():
    """Lazily initializes the Firestore Async client to prevent unnecessary overhead."""
    global _firestore_async_client
    if _firestore_async_client is None:
        try:
            # Usamos AsyncClient en lugar de Client
            _firestore_async_client = firestore.AsyncClient(database="firestore-hybrid-shield")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore Async client: {e}")
            raise
    return _firestore_async_client


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