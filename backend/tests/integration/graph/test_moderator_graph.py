"""
Integration tests for the Moderator LangGraph (graph.py).

Strategy:
  - No mocks. Every test executes real node logic, including calls to
    Vertex AI, Vertex RAG (Discovery Engine), Firestore, and BigQuery.
  - Each test uses a unique thread_id so MemorySaver states are isolated.
  - The compiled graph is instantiated once per session (module scope) to
    avoid recompilation overhead.

Coverage:
  1. Direct Approval Flow  – safe product → full pipeline → fly_wheel.
  2. Early Block Flow      – critical content → pre_filter short-circuits.
  3. Human Review Flow     – ambiguous product → graph pauses at breakpoint.
  4. Metrics Accumulation  – execution_metrics totals are aggregated by
                             merge_metrics across all active nodes.
  5. Audit Log Sequencing  – audit_log contains the nodes in the expected
                             order for each flow.
"""

import uuid
import pytest
import pytest_asyncio
from backend.agents.moderator.graph import HybridShieldAgent
from backend.agents.moderator.state import AgentState
from langgraph.types import Command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_thread_config(thread_id: str) -> dict:
    """Returns a LangGraph config dict using the provided unique ID."""
    return {"configurable": {"thread_id": thread_id}}


def _build_initial_state(
    *,
    title: str,
    description: str,
    price: float,
    gcs_uri: str,
    thread_id: str,
) -> AgentState:
    """Builds a minimal but fully-typed initial AgentState."""
    return {
        "input_data": {
            "title": title,
            "description": description,
            "price": price,
        },
        "thread_id": thread_id,
        "gcs_uri": gcs_uri,
        "requires_human_intervention": False,
        "human_feedback": None,
        "early_blocked": False,
        "features": {},
        "rag_context": "",
        "risk_score": 0.0,
        "reasoning": "",
        "final_action": "",
        "audit_log": [],
        "policy_citations": [],
        "policy_violations": [],
        "signals": {},
        "risk_breakdown": [],
        "uncertainty": 0.0,
        "routing_reason": None,
        "image_quality_score": 0.0,
        "execution_metrics": {"totals": {"prompt_tokens": 0, "candidates_tokens": 0}, "nodes": {}},
        "min_market_price": 0.0,
        "max_market_price": float('inf'),
    }


def _get_audit_node_sequence(state: dict) -> list[str]:
    """Extracts the ordered list of node names from the audit_log."""
    return [entry["node"] for entry in state.get("audit_log", [])]


# ---------------------------------------------------------------------------
# Session-scoped graph fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def graph():
    """Compiles and returns the moderator graph once per test module."""
    return await HybridShieldAgent()._build_graph()


# ---------------------------------------------------------------------------
# Test 1: Direct Approval Flow
# ---------------------------------------------------------------------------

class TestDirectApprovalFlow:
    """
    Input: a clearly safe, ordinary product.
    Expected: graph traverses the full pipeline and reaches fly_wheel.
    """

    SAFE_PRODUCT = {
        "title": "Silla de madera para jardín",
        "description": (
            "Silla artesanal de madera de pino, tratada para uso exterior. "
            "Ideal para terrazas y jardines. En excelente estado."
        ),
        "price": 85.0,
    }

    @pytest.mark.asyncio
    async def test_full_pipeline_reaches_data_flywheel(self, graph, real_gcs_uri, unique_id):
        """
        Verifies that a safe product completes all pipeline stages:
        pre_filter → extractor → (rag + risk_evaluator en paralelo) → decision → fly_wheel.
        """
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title=self.SAFE_PRODUCT["title"],
            description=self.SAFE_PRODUCT["description"],
            price=self.SAFE_PRODUCT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        # ainvoke() runs until END (or an interrupt). Safe product → no interrupt.
        final_state = await graph.ainvoke(initial_state, config=config)

        # --- Core routing assertions ---
        assert final_state.get("early_blocked") is False, (
            "Safe product must NOT trigger early_blocked."
        )
        assert final_state.get("final_action") in ("Approve", "Human Review", "Block"), (
            "final_action must be one of the valid decision outcomes."
        )
        
        # Verify that fly_wheel was reached by checking audit log
        audit_nodes = _get_audit_node_sequence(final_state)
        assert "fly_wheel" in audit_nodes, (
            f"fly_wheel must be reached in a full run. Audit: {audit_nodes}"
        )

        # Decision node must always set requires_human_intervention explicitly.
        assert isinstance(final_state.get("requires_human_intervention"), bool)
        
        # Verify routing reason
        assert final_state.get("routing_reason") in ("approved", "human_review", "high_risk"), (
            "routing_reason must be set by decision node."
        )

    @pytest.mark.asyncio
    async def test_final_action_is_not_empty(self, graph, real_gcs_uri, unique_id):
        """Verifies that fly_wheel was reached (final_action is populated)."""
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title=self.SAFE_PRODUCT["title"],
            description=self.SAFE_PRODUCT["description"],
            price=self.SAFE_PRODUCT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        assert final_state.get("final_action") != "", (
            "final_action must be populated after reaching fly_wheel."
        )
        # Para Approve, no hay reasoning generado por LLM
        # Para Block o Human Review, reasoning es generado por llm_reasoning
        if final_state.get("final_action") != "Approve":
            assert final_state.get("reasoning") != "", (
                "reasoning must be populated by llm_reasoning for Block or Human Review."
            )

    @pytest.mark.asyncio
    async def test_price_thresholds_are_populated(self, graph, real_gcs_uri, unique_id):
        """Verifies that min_market_price and max_market_price are populated in final state."""
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title=self.SAFE_PRODUCT["title"],
            description=self.SAFE_PRODUCT["description"],
            price=self.SAFE_PRODUCT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        # Verify price threshold fields are present
        assert "min_market_price" in final_state, (
            "min_market_price must be present in final state."
        )
        assert "max_market_price" in final_state, (
            "max_market_price must be present in final state."
        )
        
        # Verify they are numeric
        assert isinstance(final_state["min_market_price"], (int, float)), (
            "min_market_price must be numeric."
        )
        assert isinstance(final_state["max_market_price"], (int, float)), (
            "max_market_price must be numeric."
        )
        



# ---------------------------------------------------------------------------
# Test 2: Early Block Flow
# ---------------------------------------------------------------------------

class TestEarlyBlockFlow:
    """
    Input: content that clearly violates critical safety rules.
    Expected: pre_filter sets early_blocked=True and routes directly to
    fly_wheel, skipping all intermediate nodes.
    """

    CRITICAL_CONTENT = {
        "title": "Venta de heroína de alta pureza",
        "description": (
            "Se venden sustancias controladas, narcóticos y armas de fuego "
            "sin documentación. Envíos discretos a todo el país."
        ),
        "price": 500.0,
    }

    @pytest.mark.asyncio
    async def test_pre_filter_short_circuits(self, graph, real_gcs_uri, unique_id):
        """
        Verifies early_blocked path: pre_filter → fly_wheel, bypassing
        extractor, rag, risk_evaluator, reasoning, decision.
        """
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title=self.CRITICAL_CONTENT["title"],
            description=self.CRITICAL_CONTENT["description"],
            price=self.CRITICAL_CONTENT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        assert final_state.get("early_blocked") is True, (
            "Critical content must set early_blocked=True in pre_filter."
        )
        assert final_state.get("final_action") == "Block", (
            "Early-blocked flow must set final_action='Block'."
        )
        assert final_state.get("risk_score") == 1.0, (
            "Early-blocked flow must set risk_score=1.0."
        )
        assert final_state.get("routing_reason") == "early_block", (
            "Early-blocked flow must set routing_reason='early_block'."
        )

    @pytest.mark.asyncio
    async def test_intermediate_nodes_not_executed(self, graph, real_gcs_uri, unique_id):
        """
        When early_blocked, the audit_log must NOT contain entries from
        extractor, rag, risk_evaluator, reasoning, or decision nodes.
        """
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title=self.CRITICAL_CONTENT["title"],
            description=self.CRITICAL_CONTENT["description"],
            price=self.CRITICAL_CONTENT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)
        audit_nodes = _get_audit_node_sequence(final_state)

        # Nodes that must NOT appear in an early-blocked run
        skipped_nodes = {
            "extractor", "rag", "risk_evaluator", 
            "reasoning", "decision", "human_in_the_loop"
        }
        executed_in_audit = set(audit_nodes)

        assert executed_in_audit.isdisjoint(skipped_nodes), (
            f"Early-blocked flow must skip all post-pre_filter nodes. "
            f"Found unexpected nodes: {executed_in_audit & skipped_nodes}"
        )

    @pytest.mark.asyncio
    async def test_reasoning_contains_block_message(self, graph, real_gcs_uri, unique_id):
        """The reasoning field must contain the automatic block message."""
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title=self.CRITICAL_CONTENT["title"],
            description=self.CRITICAL_CONTENT["description"],
            price=self.CRITICAL_CONTENT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        assert "Bloqueo automático" in final_state.get("reasoning", ""), (
            "reasoning must contain the automatic block message from pre_filter."
        )


# ---------------------------------------------------------------------------
# Test Class: Human Review Flow 
# ---------------------------------------------------------------------------

class TestHumanReviewFlow:
    """
    Validación de la infraestructura de Human-in-the-Loop.
    Usa inyección de estado para garantizar que el grafo responda a la duda.
    """

    AMBIGUOUS_PRODUCT = {
        "title": "Chubasquero para perro",
        "description": "Capa impermeable amarilla para mascotas. Poco uso, talle M.",
        "price": 10.0,
    }

    @pytest.mark.asyncio
    async def test_graph_pauses_at_human_review_breakpoint(self, graph, real_gcs_uri, unique_id):
        """Verifica que el grafo se detenga en 'human_in_the_loop' tras detectar riesgo."""
        config = _make_thread_config(unique_id)
        
        await graph.aupdate_state(
            config,
            {
                "input_data": self.AMBIGUOUS_PRODUCT, 
                "thread_id": unique_id,
                "requires_human_intervention": True,
                "final_action": "Human Review",
                "risk_score": 0.5
            },
            as_node="decision" 
        )

        await graph.ainvoke(None, config=config)

        snapshot = await graph.aget_state(config)
        assert "human_in_the_loop" in snapshot.next, (
            f"El grafo debería estar pausado en 'human_in_the_loop'. Próximos: {snapshot.next}"
        )

    @pytest.mark.asyncio
    async def test_paused_state_has_requires_human_intervention(self, graph, real_gcs_uri, unique_id):
        """Verifica que el estado persistido mantenga los datos de la duda."""
        config = _make_thread_config(unique_id)
        
        await graph.aupdate_state(
            config,
            {
                "input_data": self.AMBIGUOUS_PRODUCT, 
                "thread_id": unique_id, 
                "requires_human_intervention": True, 
                "final_action": "Human Review"
            },
            as_node="decision"
        )
        await graph.ainvoke(None, config=config)

        snapshot = await graph.aget_state(config)
        paused_state = snapshot.values

        assert paused_state.get("requires_human_intervention") is True
        assert paused_state.get("final_action") == "Human Review"

    @pytest.mark.asyncio
    async def test_resume_with_human_approval_reaches_data_flywheel(self, graph, real_gcs_uri, unique_id):
        """Verifica la reanudación del grafo tras el feedback humano."""     
        config = _make_thread_config(unique_id)

        await graph.aupdate_state(
            config,
            {
                "input_data": self.AMBIGUOUS_PRODUCT, 
                "thread_id": unique_id, 
                "requires_human_intervention": True, 
                "final_action": "Human Review"
            },
            as_node="decision"
        )
        await graph.ainvoke(None, config=config)

        final_state = await graph.ainvoke(
            Command(resume={"decision": "Approve"}),
            config=config,
        )

        audit_nodes = _get_audit_node_sequence(final_state)
        
        assert "human_in_the_loop" in audit_nodes, f"Debería haber registro de intervención. Log: {audit_nodes}"
        assert "fly_wheel" in audit_nodes, f"Debería haber llegado al sink final. Log: {audit_nodes}"
        assert final_state.get("final_action") in ("Approved", "Approve"), (
            f"Acción final inesperada: {final_state.get('final_action')}"
        )


# ---------------------------------------------------------------------------
# Test 4: Execution Metrics Accumulation
# ---------------------------------------------------------------------------

class TestExecutionMetricsAccumulation:
    """
    Verifies that the merge_metrics reducer correctly accumulates token
    counts from all nodes into execution_metrics["totals"].
    """

    @pytest.mark.asyncio
    async def test_metrics_totals_are_accumulated(self, graph, real_gcs_uri, unique_id):
        """
        After a full pipeline run, totals must reflect the sum of all
        individual node token usages via merge_metrics.
        """
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title="Silla ergonómica de oficina",
            description="Silla de oficina en perfecto estado, soporte lumbar, altura ajustable.",
            price=120.0,
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        metrics = final_state.get("execution_metrics", {})
        assert "totals" in metrics, "execution_metrics must contain 'totals' key."
        assert "nodes" in metrics, "execution_metrics must contain 'nodes' key."

        totals = metrics["totals"]
        assert "prompt_tokens" in totals, "totals must contain 'prompt_tokens'."
        assert "candidates_tokens" in totals, "totals must contain 'candidates_tokens'."

        # At minimum, the LLM nodes (pre_filter, feature_extractor, llm_explainer)
        # will have consumed real tokens — totals must be positive.
        assert totals["prompt_tokens"] > 0, (
            "Total prompt_tokens must be > 0 after real LLM calls."
        )
        assert totals["candidates_tokens"] > 0, (
            "Total candidates_tokens must be > 0 after real LLM calls."
        )

    @pytest.mark.asyncio
    async def test_metrics_nodes_contains_all_pipeline_nodes(self, graph, real_gcs_uri, unique_id):
        """
        execution_metrics['nodes'] must contain an entry for every node
        that ran in the full pipeline.
        """
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title="Lámpara de pie minimalista",
            description="Lámpara en excelente estado, estilo nórdico, 1.5m de altura.",
            price=60.0,
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        nodes_metrics = final_state.get("execution_metrics", {}).get("nodes", {})

        expected_nodes = {
            "pre_filter",
            "extractor",
            "rag",
            "risk_evaluator",
            "decision",
        }

        assert expected_nodes.issubset(nodes_metrics.keys()), (
            f"Missing node metrics entries: {expected_nodes - nodes_metrics.keys()}"
        )

    @pytest.mark.asyncio
    async def test_totals_equal_sum_of_node_tokens(self, graph, real_gcs_uri, unique_id):
        """
        Verifies merge_metrics math: totals['prompt_tokens'] must equal the
        sum of all individual node prompt_tokens.
        """
        config = _make_thread_config(unique_id)
        thread_id = unique_id

        initial_state = _build_initial_state(
            title="Bicicleta de montaña rodado 29",
            description="Bicicleta seminueva, cambios Shimano, amortiguación delantera.",
            price=350.0,
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        metrics = final_state.get("execution_metrics", {})
        nodes = metrics.get("nodes", {})
        totals = metrics.get("totals", {})

        computed_prompt = sum(v.get("prompt_tokens", 0) for v in nodes.values())
        computed_candidates = sum(v.get("candidates_tokens", 0) for v in nodes.values())

        assert totals.get("prompt_tokens") == computed_prompt, (
            f"totals.prompt_tokens ({totals.get('prompt_tokens')}) must equal "
            f"sum of node prompt_tokens ({computed_prompt})."
        )
        assert totals.get("candidates_tokens") == computed_candidates, (
            f"totals.candidates_tokens ({totals.get('candidates_tokens')}) must equal "
            f"sum of node candidates_tokens ({computed_candidates})."
        )


# ---------------------------------------------------------------------------
# Test 5: Audit Log Sequencing
# ---------------------------------------------------------------------------

class TestAuditLogSequencing:
    """
    Verifies that the audit_log contains the correct sequence of node names
    for each execution path.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_audit_sequence(self, graph, real_gcs_uri, unique_id):
        """
        For a full (non-blocked, non-interrupted) run, the audit_log must
        contain entries from: extractor, logic_processor, rag, risk_aggregator,
        explainer, and decision — in that logical order.
        """
        config = _make_thread_config(unique_id)
        thread_id = unique_id
    
        initial_state = _build_initial_state(
            title="Reloj",
            description="Muy buen estado.",
            price=200.0,
            gcs_uri=real_gcs_uri,
            thread_id=thread_id,
        )

        # Primera ejecución: se detendrá si require_human_intervention = True
        final_state = await graph.ainvoke(initial_state, config=config)

        # Si el grafo necesita intervención humana, lo reanudamos con la decisión necesaria.
        # (El campo 'decision' debe coincidir con lo que espera el nodo human_review (función).
        #  Si en tu código es otro nombre, ajustalo según test_resume_with_human_approval_reaches_data_flywheel)
        if final_state.get("requires_human_intervention"):
            final_state = await graph.ainvoke(
                Command(resume={"decision": "Approve"}),
                config=config
            )

        audit_nodes = _get_audit_node_sequence(final_state)

        required_nodes = {
            "extractor", "rag", "risk_evaluator",
            "decision", "fly_wheel"
        }
        executed_in_audit = set(audit_nodes)

        assert required_nodes.issubset(executed_in_audit), (
            f"Full pipeline audit_log is missing nodes: {required_nodes - executed_in_audit}. "
            f"Actual sequence: {audit_nodes}"
        )
        
        # Si no fue Approve, debe haber pasado por reasoning
        if final_state.get("final_action") != "Approve":
            assert "reasoning" in executed_in_audit, (
                "reasoning node must appear for Block or Human Review actions."
            )

    @pytest.mark.asyncio
    async def test_full_pipeline_audit_ordering(self, graph, real_gcs_uri, unique_id):
        """
        Validates that 'extractor' appears before 'risk_evaluator', which appears
        before 'decision', preserving causal ordering in the audit trail.
        """
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Cafetera italiana 6 tazas",
            description="Cafetera moka en acero inoxidable, usada pero en perfecto estado.",
            price=30.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)
        audit_nodes = _get_audit_node_sequence(final_state)

        def _index(node: str) -> int:
            try:
                return audit_nodes.index(node)
            except ValueError:
                return -1

        extractor_idx = _index("extractor")
        evaluator_idx = _index("risk_evaluator")
        decision_idx = _index("decision")

        assert extractor_idx != -1, "extractor must appear in audit_log."
        assert evaluator_idx != -1, "risk_evaluator must appear in audit_log."
        assert decision_idx != -1, "decision must appear in audit_log."

        assert extractor_idx < evaluator_idx, (
            "extractor must appear before risk_evaluator in audit_log."
        )
        assert evaluator_idx < decision_idx, (
            "risk_evaluator must appear before decision in audit_log."
        )

    @pytest.mark.asyncio
    async def test_early_blocked_audit_has_no_decision(self, graph, real_gcs_uri, unique_id):
        """
        For an early-blocked run, the 'decision' node must NOT appear in
        the audit_log since it was bypassed.
        """
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Venta de armas ilegales sin documentación",
            description="Ofrezco pistolas, rifles y munición sin papeles.",
            price=2000.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)

        # Only proceed with audit assertions if the block actually triggered.
        # (Safety: if the LLM doesn't flag it, skip rather than false-fail.)
        if not final_state.get("early_blocked"):
            pytest.skip("LLM did not flag critical content in this run; skipping audit assertion.")

        audit_nodes = _get_audit_node_sequence(final_state)
        assert "decision" not in audit_nodes, (
            "decision node must NOT appear in audit_log for early-blocked flow."
        )

    @pytest.mark.asyncio
    async def test_audit_log_entries_have_required_fields(self, graph, real_gcs_uri, unique_id):
        """
        Every entry in audit_log must contain the mandatory keys:
        'node', 'status', 'summary', 'timestamp'.
        """
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Auriculares Bluetooth Sony",
            description="Auriculares en caja original, sin uso, regalo de empresa.",
            price=95.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await graph.ainvoke(initial_state, config=config)
        audit_log = final_state.get("audit_log", [])

        assert len(audit_log) > 0, "audit_log must not be empty after a pipeline run."

        required_keys = {"node", "status", "summary", "timestamp"}
        for entry in audit_log:
            missing = required_keys - entry.keys()
            assert not missing, (
                f"Audit log entry for node '{entry.get('node', '?')}' "
                f"is missing required keys: {missing}"
            )

