import logging
from datetime import datetime, timezone
from google.cloud import firestore

logger = logging.getLogger("moderation_pipeline")

# Lazy Global Client
_firestore_client = None

def get_firestore_client():
    """Lazily initializes the Firestore client to prevent unnecessary overhead."""
    global _firestore_client
    if _firestore_client is None:
        try:
            _firestore_client = firestore.Client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise
    return _firestore_client

def update_job_status(thread_id: str, status: str, metadata: dict = None):
    """
    Updates the status and metadata of a moderation job in Firestore.
    
    Args:
        thread_id: The identifier for the job (document ID).
        status: The current phase or status of the job.
        metadata: Optional dictionary with extra data to merge into the document.
    """
    if not thread_id:
        logger.warning("Job status update skipped: thread_id is missing")
        return

    try:
        db = get_firestore_client()
        doc_ref = db.collection("jobs").document(thread_id)
        
        payload = {
            "status": status,
            "last_update": datetime.now(timezone.utc)
        }
        
        if metadata:
            payload.update(metadata)
        
        # Using merge=True ensures we don't overwrite other unrelated fields 
        # and creates the document if it doesn't exist.
        doc_ref.set(payload, merge=True)
        
        logger.info(f"Firestore update successful: phase='{status}', job_id='{thread_id}'")
        
    except Exception as e:
        logger.error(f"Firestore update failed for job_id '{thread_id}': {e}")
