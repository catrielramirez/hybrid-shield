import logging
from ..services import firestore_service

logger = logging.getLogger("moderation_pipeline")


async def emit_status(
    thread_id: str,
    node: str,
    status: str,
    ui_context: str,
    ui_message: str
):
    try:
        await firestore_service.update_job_status(thread_id, status)
        await firestore_service.update_ui_state(
            thread_id,
            current_node=node,
            ui_context=ui_context,
            ui_message=ui_message,
            status=status
        )
    except Exception as e:
        logger.error(f"Error updating Firestore status for node {node}: {e}", exc_info=True)
