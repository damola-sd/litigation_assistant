"""
Tests for POST /analyze — the core SSE pipeline.

All 4 agents and RAG are mocked via the `mock_agents` fixture so tests run
instantly with zero API cost. Override mock_agents["<step>"].side_effect to
simulate failures in specific agents.

SSE event shape reference:
  Running:  {"step": str, "status": "running", "step_index": int}
  Done:     {"step": str, "status": "done",    "step_index": int, "result": dict}
  Complete: {"event": "complete", "analysis_id": str}
  Error:    {"event": "error",   "detail": str}
"""

import uuid

import pytest

from tests.conftest import HEADERS_A, SAMPLE_CASE, collect_sse, run_analyze

EXPECTED_STEPS = ["extraction", "rag_retrieval", "strategy", "drafting", "qa"]


# ── Input validation ──────────────────────────────────────────────────────────


async def test_empty_string_returns_422(client):
    r = await client.post("/analyze", json={"case_text": ""}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_whitespace_only_returns_422(client):
    r = await client.post("/analyze", json={"case_text": "   \n\t  "}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_missing_case_text_field_returns_422(client):
    r = await client.post("/analyze", json={}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_invalid_json_body_returns_422(client):
    r = await client.post(
        "/analyze",
        content=b"not-json",
        headers={**HEADERS_A, "Content-Type": "application/json"},
    )
    assert r.status_code == 422


async def test_extra_fields_are_ignored(client, mock_agents):
    """Unknown fields should not cause a 422 — Pydantic ignores extras by default."""
    async with client.stream(
        "POST",
        "/analyze",
        json={"case_text": SAMPLE_CASE, "unknown_field": "should_be_ignored"},
        headers=HEADERS_A,
    ) as resp:
        assert resp.status_code == 200


# ── Happy-path SSE structure ──────────────────────────────────────────────────


async def test_pipeline_returns_200_with_event_stream(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]


async def test_pipeline_emits_exactly_11_events(client, mock_agents):
    """5 steps × (running + done) + 1 complete = 11 events."""
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert len(events) == 11


async def test_last_event_is_complete(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert events[-1].get("event") == "complete"


async def test_complete_event_contains_analysis_id(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert "analysis_id" in events[-1]


async def test_analysis_id_is_valid_uuid(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    # uuid.UUID raises ValueError if the string is not a valid UUID
    uuid.UUID(events[-1]["analysis_id"])


async def test_done_steps_arrive_in_correct_order(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    done_steps = [e["step"] for e in events if e.get("status") == "done"]
    assert done_steps == EXPECTED_STEPS


async def test_running_event_precedes_done_for_every_step(client, mock_agents):
    """For each agent, its 'running' event must appear before its 'done' event."""
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    step_events = [e for e in events if "step" in e]
    for name in EXPECTED_STEPS:
        pair = [e for e in step_events if e["step"] == name]
        assert len(pair) == 2, f"Expected 2 events for {name}, got {len(pair)}"
        assert pair[0]["status"] == "running"
        assert pair[1]["status"] == "done"


async def test_step_indices_are_0_through_4(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    done_indices = [e["step_index"] for e in events if e.get("status") == "done"]
    assert done_indices == [0, 1, 2, 3, 4]


# ── Per-step result shape ─────────────────────────────────────────────────────


async def test_extraction_result_has_facts_entities_timeline(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    result = next(
        e["result"] for e in events if e.get("step") == "extraction" and e.get("status") == "done"
    )
    assert isinstance(result["facts"], list) and len(result["facts"]) > 0
    assert isinstance(result["entities"], list) and len(result["entities"]) > 0
    assert isinstance(result["timeline"], list) and len(result["timeline"]) > 0


async def test_rag_result_has_chunks_key(client, mock_agents):
    """Amit's stub returns [] — the key must still be present for the frontend."""
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    result = next(
        e["result"]
        for e in events
        if e.get("step") == "rag_retrieval" and e.get("status") == "done"
    )
    assert "chunks" in result


async def test_strategy_result_has_required_keys(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    result = next(
        e["result"] for e in events if e.get("step") == "strategy" and e.get("status") == "done"
    )
    for key in ["legal_issues", "applicable_laws", "arguments", "counterarguments", "legal_reasoning"]:
        assert key in result, f"Missing key: {key}"


async def test_drafting_brief_has_all_5_fields(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    brief = next(
        e["result"]["brief"]
        for e in events
        if e.get("step") == "drafting" and e.get("status") == "done"
    )
    for field in ["facts", "issues", "arguments", "counterarguments", "conclusion"]:
        assert field in brief, f"Brief missing field: {field}"


async def test_qa_risk_level_is_valid_value(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    result = next(
        e["result"] for e in events if e.get("step") == "qa" and e.get("status") == "done"
    )
    assert result["risk_level"] in {"low", "medium", "high"}
    assert isinstance(result["is_grounded"], bool)


# ── Agent call counts ─────────────────────────────────────────────────────────


async def test_each_agent_called_exactly_once(client, mock_agents):
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    mock_agents["extraction"].assert_called_once()
    mock_agents["rag"].assert_called_once()
    mock_agents["strategy"].assert_called_once()
    mock_agents["drafting"].assert_called_once()
    mock_agents["qa"].assert_called_once()


async def test_strategy_receives_extraction_output(client, mock_agents):
    """Strategy agent must receive the extraction result as its first argument."""
    from tests.conftest import MOCK_EXTRACTION

    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    call_args = mock_agents["strategy"].call_args
    assert call_args.args[0] == MOCK_EXTRACTION


async def test_drafting_receives_extraction_and_strategy(client, mock_agents):
    from tests.conftest import MOCK_EXTRACTION, MOCK_STRATEGY

    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    call_args = mock_agents["drafting"].call_args
    assert call_args.args[0] == MOCK_EXTRACTION
    assert call_args.args[1] == MOCK_STRATEGY


# ── Error handling ────────────────────────────────────────────────────────────


async def test_extraction_failure_emits_error_event(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("OpenAI rate limit exceeded")

    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)

    last = events[-1]
    assert last.get("event") == "error"
    assert "rate limit" in last.get("detail", "").lower()


async def test_mid_pipeline_failure_still_emits_completed_earlier_steps(client, mock_agents):
    """When strategy fails, extraction + rag_retrieval should already be done."""
    mock_agents["strategy"].side_effect = RuntimeError("Strategy agent failed")

    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)

    completed = {e["step"] for e in events if e.get("status") == "done"}
    assert "extraction" in completed
    assert "rag_retrieval" in completed
    assert "strategy" not in completed


async def test_failure_last_event_is_error_not_complete(client, mock_agents):
    mock_agents["qa"].side_effect = RuntimeError("QA failed")

    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)

    assert events[-1].get("event") == "error"
    assert not any(e.get("event") == "complete" for e in events)


async def test_failed_case_saved_with_failed_status(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("boom")

    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)

    history = (await client.get("/history", headers=HEADERS_A)).json()
    assert len(history) == 1
    assert history[0]["status"] == "failed"


async def test_server_continues_serving_after_pipeline_error(client, mock_agents):
    """A failed pipeline must not crash the server — next request must succeed."""
    mock_agents["extraction"].side_effect = RuntimeError("boom")
    async with client.stream(
        "POST", "/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)

    # Reset and verify a fresh request succeeds
    mock_agents["extraction"].side_effect = None
    r = await client.get("/health")
    assert r.status_code == 200
