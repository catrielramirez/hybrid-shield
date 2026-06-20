import logging
import os
import google.auth
from typing import Dict, Any, Optional
from langgraph.types import Command
from ..graph import HybridShieldAgent

logger = logging.getLogger("moderation_pipeline")

# Patrón Singleton para el agente
_agent_instance: Optional[HybridShieldAgent] = None

def _get_agent() -> HybridShieldAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HybridShieldAgent()
        
        _, default_project_id = google.auth.default()
        
        if not getattr(_agent_instance, "project", None):
            _agent_instance.project = os.getenv("PROJECT_ID") or default_project_id
        if not getattr(_agent_instance, "region", None):
            _agent_instance.region = os.getenv("GCP_REGION") or "us-central1"
        if not getattr(_agent_instance, "instance_name", None):
            instance = os.getenv("DB_INSTANCE_NAME")
            if not instance:
                raise ValueError("ERROR: DB_INSTANCE_NAME no configurado.")
            _agent_instance.instance_name = instance
            
    return _agent_instance

async def get_full_audit_trace(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Recupera el historial completo de ejecución de un thread desde Postgres
    utilizando el checkpointer del agente compilado.
    """
    try:
        agent = _get_agent()
        # Aseguramos que el grafo y el checkpointer estén inicializados una única vez
        await agent._build_graph()
        
        if getattr(agent, "checkpointer", None) is None:
            raise RuntimeError("El grafo no tiene un checkpointer configurado.")
            
        config = {"configurable": {"thread_id": thread_id}}
        
        history = []
        # Iteramos de forma asíncrona sobre el historial del hilo
        async for checkpoint_tuple in agent.checkpointer.alist(config):
            # Extraemos los valores de los canales de estado
            state_values = checkpoint_tuple.checkpoint.get("channel_values", {})
            
            # Limpiamos el estado para no enviar binarios/blobs pesados al frontend
            clean_state = {k: v for k, v in state_values.items() if not k.startswith("__")}

            # Determinamos el nombre real del nodo ejecutado usando el audit_log
            audit_log = clean_state.get("audit_log", [])
            real_node = "START"
            if audit_log:
                real_node = audit_log[-1].get("node", "UNKNOWN")
            else:
                source = checkpoint_tuple.metadata.get("source") if checkpoint_tuple.metadata else None
                if source and source != "loop":
                    real_node = source

            history.append({
                "checkpoint_id": checkpoint_tuple.config["configurable"].get("checkpoint_id"),
                "timestamp": checkpoint_tuple.metadata.get("ts") if checkpoint_tuple.metadata else None,
                "next_node": real_node,
                "state": clean_state
            })
            
        if not history:
            return None
            
        # El primer elemento es el más reciente debido al orden de aget_history
        latest_state = history[0].get("state", {})
        
        audit_log = latest_state.get("audit_log", [])
        trace_items = []
        
        if audit_log:
            for entry in audit_log:
                node_name = entry.get("node", "UNKNOWN")
                virtual_state = {}
                if entry.get("summary"):
                    virtual_state["resumen"] = entry.get("summary")
                if entry.get("data"):
                    virtual_state["detalles"] = entry.get("data")
                if entry.get("evidence"):
                    virtual_state["evidencia"] = entry.get("evidence")
                
                trace_items.append({
                    "checkpoint_id": entry.get("checkpoint_id", f"audit_{node_name.lower()}"),
                    "timestamp": entry.get("timestamp"),
                    "next_node": node_name.upper(),
                    "status": entry.get("status", "completed"),
                    "state": virtual_state
                })
            # Reversamos para que el formato sea "más reciente primero", coincidiendo con history
            trace_items.reverse()
        else:
            trace_items = history
            
        return {
            "thread_id": thread_id,
            "latest_state": latest_state,
            "history_length": len(history),
            "trace": trace_items
        }
        
    except Exception as e:
        logger.error(f"Error fetching full trace for thread {thread_id}: {e}", exc_info=True)
        raise Exception(f"Database read error: {e}")

async def resume_graph_execution(thread_id: str, action: str, justification: Optional[str] = None) -> Dict[str, Any]:
    """
    Función de Escritura (Command): Retoma la ejecución del grafo compilado,
    inyectando la decisión humana.
    """
    try:
        agent = _get_agent()
        # Necesitamos el grafo compilado para hacer ainvoke y reanudar la ejecución
        app = await agent._build_graph()
        
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.info(f"Resuming graph for thread {thread_id} with action: {action}")
        
        # Ejecuta la reanudación inyectando el valor en el nodo interrumpido (human_in_the_loop)
        resume_payload = {"decision": action}
        if justification:
            resume_payload["justification"] = justification
            
        result = await app.ainvoke(Command(resume=resume_payload), config=config)
        
        return {
            "thread_id": thread_id,
            "status": "resumed",
            "final_action": result.get("final_action") if isinstance(result, dict) else None
        }
        
    except Exception as e:
        logger.error(f"Error resuming graph execution for thread {thread_id}: {e}", exc_info=True)
        try:
            from .firestore_service import update_job_status, update_ui_state
            await update_job_status(
                thread_id, 
                "FAILED", 
                {
                    "error_message": f"Resumption failure: {str(e)}",
                    "metadata": {"error": f"Failed to resume graph: {str(e)}"}
                }
            )
            await update_ui_state(
                thread_id,
                current_node="human_in_the_loop",
                ui_context="error",
                ui_message=f"Error al reanudar el job: {str(e)}",
                status="FAILED"
            )
        except Exception as fe:
            logger.error(f"Failed to update Firestore status on resumption error: {fe}", exc_info=True)
        raise Exception(f"Graph execution error: {e}")
