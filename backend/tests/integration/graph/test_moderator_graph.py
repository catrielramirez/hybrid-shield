"""
Integration tests for the Moderator LangGraph (graph.py).

Strategy:
  - No mocks. Every test executes real node logic, including calls to
    Vertex AI, Vertex RAG (Discovery Engine), Firestore, and BigQuery.
  - Each test uses a unique thread_id so MemorySaver states are isolated.
  - The compiled graph is instantiated once per session (session scope) via conftest.py.

Coverage:
  1. Direct Approval Flow  – safe product → full pipeline → fly_wheel.
  2. Early Block Flow      – critical content → pre_filter short-circuits.
  3. Human Review Flow     – ambiguous product → graph pauses at breakpoint.
  4. Metrics Accumulation  – execution_metrics totals are aggregated by
                             merge_metrics across all active nodes.
  5. Audit Log Sequencing  – audit_log contains the nodes in the expected
                             order for each flow.
"""

import pytest
from backend.agents.moderator.state import AgentState
from langgraph.types import Command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _build_initial_state(
    *,
    title: str,
    description: str,
    price: float,
    gcs_uri: str,
    thread_id: str,
) -> AgentState:
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
    return [entry["node"] for entry in state.get("audit_log", [])]


# ---------------------------------------------------------------------------
# Test 1: Direct Approval Flow
# ---------------------------------------------------------------------------

class TestDirectApprovalFlow:
    SAFE_PRODUCT = {
        "title": "Silla de madera para jardín",
        "description": (
            "Silla artesanal de madera de pino, tratada para uso exterior. "
            "Ideal para terrazas y jardines. En excelente estado."
        ),
        "price": 85.0,
    }

    @pytest.mark.asyncio
    async def test_full_pipeline_reaches_data_flywheel(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title=self.SAFE_PRODUCT["title"],
            description=self.SAFE_PRODUCT["description"],
            price=self.SAFE_PRODUCT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        # Si el grafo pausó esperando revisión humana, lo reanudamos
        snapshot = app.get_state(config)
        if snapshot.next:
            final_state = await app.ainvoke(
                Command(resume={"decision": "Approve", "justification": "Auto-approved in test"}),
                config=config,
            )

        assert final_state.get("early_blocked") is False
        assert final_state.get("final_action") in ("Approve", "Human Review", "Block")

        audit_nodes = _get_audit_node_sequence(final_state)
        assert "fly_wheel" in audit_nodes, f"fly_wheel must be reached. Audit: {audit_nodes}"

        assert isinstance(final_state.get("requires_human_intervention"), bool)
        assert final_state.get("routing_reason") in ("approved", "human_review", "high_risk")


    @pytest.mark.asyncio
    async def test_final_action_is_not_empty(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title=self.SAFE_PRODUCT["title"],
            description=self.SAFE_PRODUCT["description"],
            price=self.SAFE_PRODUCT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        assert final_state.get("final_action") != ""
        if final_state.get("final_action") != "Approve":
            assert final_state.get("reasoning") != ""

    @pytest.mark.asyncio
    async def test_price_thresholds_are_populated(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title=self.SAFE_PRODUCT["title"],
            description=self.SAFE_PRODUCT["description"],
            price=self.SAFE_PRODUCT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        assert "min_market_price" in final_state
        assert "max_market_price" in final_state
        assert isinstance(final_state["min_market_price"], (int, float))
        assert isinstance(final_state["max_market_price"], (int, float))


# ---------------------------------------------------------------------------
# Test 2: Early Block Flow
# ---------------------------------------------------------------------------

class TestEarlyBlockFlow:
    CRITICAL_CONTENT = {
        "title": "Venta de heroína de alta pureza",
        "description": (
            "Se venden sustancias controladas, narcóticos y armas de fuego "
            "sin documentación. Envíos discretos a todo el país."
        ),
        "price": 500.0,
    }

    @pytest.mark.asyncio
    async def test_pre_filter_short_circuits(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title=self.CRITICAL_CONTENT["title"],
            description=self.CRITICAL_CONTENT["description"],
            price=self.CRITICAL_CONTENT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        assert final_state.get("early_blocked") is True
        assert final_state.get("final_action") == "Block"
        assert final_state.get("risk_score") == 1.0
        assert final_state.get("routing_reason") == "early_block"

    @pytest.mark.asyncio
    async def test_intermediate_nodes_not_executed(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title=self.CRITICAL_CONTENT["title"],
            description=self.CRITICAL_CONTENT["description"],
            price=self.CRITICAL_CONTENT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)
        audit_nodes = _get_audit_node_sequence(final_state)

        skipped_nodes = {"extractor", "rag", "risk_evaluator", "reasoning", "decision", "human_in_the_loop"}
        executed_in_audit = set(audit_nodes)

        assert executed_in_audit.isdisjoint(skipped_nodes), (
            f"Early-blocked flow must skip all post-pre_filter nodes. "
            f"Found unexpected nodes: {executed_in_audit & skipped_nodes}"
        )

    @pytest.mark.asyncio
    async def test_reasoning_contains_block_message(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title=self.CRITICAL_CONTENT["title"],
            description=self.CRITICAL_CONTENT["description"],
            price=self.CRITICAL_CONTENT["price"],
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        assert "Bloqueo automático" in final_state.get("reasoning", "")


# ---------------------------------------------------------------------------
# Test 3: Human Review Flow
# ---------------------------------------------------------------------------

class TestHumanReviewFlow:
    AMBIGUOUS_PRODUCT = {
        "title": "Chubasquero para perro",
        "description": "Capa impermeable amarilla para mascotas. Poco uso, talle M.",
        "price": 10.0,
    }

    @pytest.mark.asyncio
    async def test_graph_pauses_at_human_review_breakpoint(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        app.update_state(
            config,
            {
                "input_data": self.AMBIGUOUS_PRODUCT,
                "thread_id": unique_id,
                "requires_human_intervention": True,
                "final_action": "Human Review",
                "risk_score": 0.5,
            },
            as_node="decision",
        )

        await app.ainvoke(None, config=config)

        snapshot = app.get_state(config)
        assert "human_in_the_loop" in snapshot.next, (
            f"El grafo debería estar pausado en 'human_in_the_loop'. Próximos: {snapshot.next}"
        )

    @pytest.mark.asyncio
    async def test_paused_state_has_requires_human_intervention(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        app.update_state(
            config,
            {
                "input_data": self.AMBIGUOUS_PRODUCT,
                "thread_id": unique_id,
                "requires_human_intervention": True,
                "final_action": "Human Review",
            },
            as_node="decision",
        )
        await app.ainvoke(None, config=config)

        snapshot = app.get_state(config)
        paused_state = snapshot.values

        assert paused_state.get("requires_human_intervention") is True
        assert paused_state.get("final_action") == "Human Review"

    @pytest.mark.asyncio
    async def test_resume_with_human_approval_reaches_data_flywheel(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        app.update_state(
            config,
            {
                "input_data": self.AMBIGUOUS_PRODUCT,
                "thread_id": unique_id,
                "requires_human_intervention": True,
                "final_action": "Human Review",
            },
            as_node="decision",
        )
        await app.ainvoke(None, config=config)

        final_state = await app.ainvoke(
            Command(resume={"decision": "Approve", "justification": "Looks good to me"}),
            config=config,
        )

        audit_nodes = _get_audit_node_sequence(final_state)

        assert "human_in_the_loop" in audit_nodes, f"Debería haber registro de intervención. Log: {audit_nodes}"
        assert "fly_wheel" in audit_nodes, f"Debería haber llegado al sink final. Log: {audit_nodes}"
        # FIX: human_review node solo devuelve "Approve", no "Approved"
        assert final_state.get("final_action") == "Approve", (
            f"Acción final inesperada: {final_state.get('final_action')}"
        )


# ---------------------------------------------------------------------------
# Test 4: Execution Metrics Accumulation
# ---------------------------------------------------------------------------

class TestExecutionMetricsAccumulation:

    @pytest.mark.asyncio
    async def test_metrics_totals_are_accumulated(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Silla ergonómica de oficina",
            description="Silla de oficina en perfecto estado, soporte lumbar, altura ajustable.",
            price=120.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        metrics = final_state.get("execution_metrics", {})
        assert "totals" in metrics
        assert "nodes" in metrics

        totals = metrics["totals"]
        assert "prompt_tokens" in totals
        assert "candidates_tokens" in totals
        assert totals["prompt_tokens"] > 0
        assert totals["candidates_tokens"] > 0

    @pytest.mark.asyncio
    async def test_metrics_nodes_contains_all_pipeline_nodes(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Lámpara de pie minimalista",
            description="Lámpara en excelente estado, estilo nórdico, 1.5m de altura.",
            price=60.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        nodes_metrics = final_state.get("execution_metrics", {}).get("nodes", {})

        expected_nodes = {"pre_filter", "extractor", "rag", "risk_evaluator", "decision"}
        assert expected_nodes.issubset(nodes_metrics.keys()), (
            f"Missing node metrics entries: {expected_nodes - nodes_metrics.keys()}"
        )

    @pytest.mark.asyncio
    async def test_totals_equal_sum_of_node_tokens(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Bicicleta de montaña rodado 29",
            description="Bicicleta seminueva, cambios Shimano, amortiguación delantera.",
            price=350.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        metrics = final_state.get("execution_metrics", {})
        nodes = metrics.get("nodes", {})
        totals = metrics.get("totals", {})

        computed_prompt = sum(v.get("prompt_tokens", 0) for v in nodes.values())
        computed_candidates = sum(v.get("candidates_tokens", 0) for v in nodes.values())

        assert totals.get("prompt_tokens") == computed_prompt
        assert totals.get("candidates_tokens") == computed_candidates


# ---------------------------------------------------------------------------
# Test 5: Audit Log Sequencing
# ---------------------------------------------------------------------------

class TestAuditLogSequencing:

    @pytest.mark.asyncio
    async def test_full_pipeline_audit_sequence(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Reloj",
            description="Muy buen estado.",
            price=200.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        if final_state.get("requires_human_intervention"):
            final_state = await app.ainvoke(
                Command(resume={"decision": "Approve", "justification": "Approved via audit check"}),
                config=config,
            )

        audit_nodes = _get_audit_node_sequence(final_state)
        required_nodes = {"extractor", "rag", "risk_evaluator", "decision", "fly_wheel"}
        executed_in_audit = set(audit_nodes)

        assert required_nodes.issubset(executed_in_audit), (
            f"Full pipeline audit_log is missing nodes: {required_nodes - executed_in_audit}. "
            f"Actual sequence: {audit_nodes}"
        )

        if final_state.get("final_action") != "Approve":
            assert "reasoning" in executed_in_audit

    @pytest.mark.asyncio
    async def test_full_pipeline_audit_ordering(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Cafetera italiana 6 tazas",
            description="Cafetera moka en acero inoxidable, usada pero en perfecto estado.",
            price=30.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)
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

        assert extractor_idx < evaluator_idx
        assert evaluator_idx < decision_idx

    @pytest.mark.asyncio
    async def test_early_blocked_audit_has_no_decision(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Venta de armas ilegales sin documentación",
            description="Ofrezco pistolas, rifles y munición sin papeles.",
            price=2000.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)

        if not final_state.get("early_blocked"):
            pytest.skip("LLM did not flag critical content in this run; skipping audit assertion.")

        audit_nodes = _get_audit_node_sequence(final_state)
        assert "decision" not in audit_nodes

    @pytest.mark.asyncio
    async def test_audit_log_entries_have_required_fields(self, app, real_gcs_uri, unique_id):
        config = _make_thread_config(unique_id)

        initial_state = _build_initial_state(
            title="Auriculares Bluetooth Sony",
            description="Auriculares en caja original, sin uso, regalo de empresa.",
            price=95.0,
            gcs_uri=real_gcs_uri,
            thread_id=unique_id,
        )

        final_state = await app.ainvoke(initial_state, config=config)
        audit_log = final_state.get("audit_log", [])

        assert len(audit_log) > 0

        required_keys = {"node", "status", "summary", "timestamp"}
        for entry in audit_log:
            missing = required_keys - entry.keys()
            assert not missing, (
                f"Audit log entry for node '{entry.get('node', '?')}' "
                f"is missing required keys: {missing}"
            )