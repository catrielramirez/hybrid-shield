import os
import asyncio
from langgraph.graph import StateGraph, END
from langchain_google_cloud_sql_pg import PostgresEngine
try:
    from langchain_google_cloud_sql_pg import PostgresSaver
except ImportError:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver as PostgresSaver

from .state import AgentState
from .nodes import (
    pre_filter_node,
    feature_extractor_node,
    rag_node,
    risk_evaluator_node,
    llm_reasoning_node,
    decision_node,
    human_review,
    data_flywheel_node,
)

class HybridShieldAgent:
    """
    Agente de Moderación Empaquetado para Vertex AI Reasoning Engine.
    Implementa Lazy Initialization para la capa de persistencia y el compilado
    del grafo para evitar fallos de serialización con cloudpickle.
    """
    def __init__(self):
        self.app = None
        self.checkpointer = None
        self.engine = None

    async def _initialize_checkpointer(self):
        """Inicializa el checkpointer y la base de datos de manera perezosa."""
        if self.checkpointer is not None:
            return self.checkpointer

        # CAPTURA CLAVE: Buscamos el diccionario inyectado dinámicamente.
        # Si no existe (ej. corriendo en local), devuelve un diccionario vacío {}
        config_env = getattr(self, "env_vars", {})

        # Buscamos primero en el diccionario inyectado; si no está, usamos os.getenv
        conn_name = config_env.get("DB_CONNECTION_NAME") or os.getenv("DB_CONNECTION_NAME", "")
        
        parts = conn_name.split(":")
        project_id = parts[0] if len(parts) > 0 else (config_env.get("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT"))
        region = parts[1] if len(parts) > 1 else "us-central1"
        instance = parts[2] if len(parts) > 2 else ""

        db_kwargs = {
            "project_id": project_id,
            "region": region,
            "instance": instance,
            "database": config_env.get("DB_NAME") or os.getenv("DB_NAME", "agent_states")
        }
        
        db_user = config_env.get("DB_USER") or os.getenv("DB_USER")
        db_pass = config_env.get("DB_PASS") or os.getenv("DB_PASS")
        
        if db_user and db_pass:
            db_kwargs["user"] = db_user
            db_kwargs["password"] = db_pass
            
        self.engine = await PostgresEngine.afrom_instance(**db_kwargs)

        try:
            await self.engine.ainit_checkpoint_table(table_name="checkpoints")
        except Exception as e:
            if "already exists" not in str(e):
                raise e

        self.checkpointer = await PostgresSaver.create(self.engine, table_name="checkpoints")
        return self.checkpointer
        

    async def _build_graph(self):
        """Construye y compila el flujo de trabajo de manera perezosa."""
        if self.app is not None:
            return self.app

        # pyrefly: ignore [bad-specialization]
        workflow = StateGraph(AgentState)

        # Definición de Nodos
        workflow.add_node("pre_filter", pre_filter_node)
        workflow.add_node("extractor", feature_extractor_node)
        workflow.add_node("rag", rag_node)
        workflow.add_node("risk_evaluator", risk_evaluator_node)
        workflow.add_node("reasoning", llm_reasoning_node)
        workflow.add_node("decision", decision_node)
        workflow.add_node("human_in_the_loop", human_review)
        workflow.add_node("fly_wheel", data_flywheel_node)

        # Punto de entrada inicial
        workflow.set_entry_point("pre_filter")

        # Enrutamiento condicional tras el pre-filtrado
        def route_after_pre_filter(state: AgentState):
            if state.get("early_blocked"):
                return "fly_wheel"
            return "extractor"

        workflow.add_conditional_edges(
            "pre_filter", route_after_pre_filter,
            {"fly_wheel": "fly_wheel", "extractor": "extractor"}
        )

        # Condicional desde extractor: derivar directo a HITL si es ambiguo o poca confianza
        def route_after_extractor(state: AgentState):
            features = state.get("features") or {}
            try:
                confidence = float(features.get("confidence", 1.0))
            except (ValueError, TypeError):
                confidence = 1.0
                
            if features.get("image_quality") == "ambiguous" or confidence < 0.60:
                return ["human_in_the_loop"]
            return ["risk_evaluator", "rag"]

        workflow.add_conditional_edges(
            "extractor", route_after_extractor,
            {"human_in_the_loop": "human_in_the_loop", "risk_evaluator": "risk_evaluator", "rag": "rag"}
        )

        # Fan-in: Ambos convergen en decision
        workflow.add_edge("risk_evaluator", "decision")
        workflow.add_edge("rag", "decision")

        def route_post_decision(state: AgentState):
            # Primero verificamos si se requiere intervención, sin importar la acción final
            if state.get("requires_human_intervention"):
                return "reasoning"
            
            action = state.get("final_action")
            
            if action == "Approve":
                return "fly_wheel"
            else:  # Block o Human Review
                return "reasoning"

        workflow.add_conditional_edges(
            "decision", route_post_decision,
            {"fly_wheel": "fly_wheel", "reasoning": "reasoning"}
        )

        # Nuevo enrutamiento condicional desde reasoning
        def route_post_explainer(state: AgentState):
            if state.get("requires_human_intervention"):
                return "human_in_the_loop"
            else:
                return "fly_wheel"

        workflow.add_conditional_edges(
            "reasoning", route_post_explainer,
            {"human_in_the_loop": "human_in_the_loop", "fly_wheel": "fly_wheel"}
        )

        # Enrutamiento condicional seguro para el feedback humano
        def route_post_human(state: AgentState):
            if state.get("requires_human_intervention"):
                return "human_in_the_loop"
            return "fly_wheel"

        workflow.add_conditional_edges(
            "human_in_the_loop", route_post_human,
            {"human_in_the_loop": "human_in_the_loop", "fly_wheel": "fly_wheel"}
        )

        # Cierre de estados finales
        workflow.add_edge("fly_wheel", END)

        # Inicialización de la capa de persistencia perezosa
        checkpointer = await self._initialize_checkpointer()

        # Compilación final
        self.app = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["human_in_the_loop"]
        )
        return self.app

    def set_up(self):
        """Inicialización diferida: se ejecuta en el entorno remoto al arrancar."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # El loop ya está corriendo (ej. Uvicorn), programamos la tarea
                loop.create_task(self._build_graph())
            else:
                loop.run_until_complete(self._build_graph())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._build_graph())

    def query(self, input_data: dict) -> dict:
        """
        Punto de entrada sincrónico esperado por Vertex AI Agent Engine.
        Envuelve la llamada asincrónica de LangGraph para evitar bloqueos del loop de eventos.
        """
        gcs_uri = input_data.get("gcs_uri")
        thread_id = input_data.get("thread_id", "default-thread")
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "input_data": input_data,
            "gcs_uri": gcs_uri,
            "thread_id": thread_id
        }

        async def _run_graph():
            app = await self._build_graph()
            return await app.ainvoke(initial_state, config=config)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Si ya hay un loop corriendo, corremos en un thread separado de forma síncrona
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run_graph())
                return future.result()
        else:
            return loop.run_until_complete(_run_graph())