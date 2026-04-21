"""
Tests for POST /api/v1/analyze — the core SSE pipeline.

SSE event shape reference:
  Running:  {"step": str, "status": "running",   "step_index": int}
  Done:     {"step": str, "status": "completed", "step_index": int, "data": dict}
  Final:    {"step": "done", "status": "completed", "case_id": str}
  Error:    {"event": "error", "detail": str}
"""

import uuid

import pytest

from tests.conftest import HEADERS_A, SAMPLE_CASE, collect_sse, run_analyze

EXPECTED_STEPS = ["extraction", "rag_retrieval", "strategy", "drafting", "qa"]


# ── Input validation ──────────────────────────────────────────────────────────


async def test_empty_string_returns_422(client):
    r = await client.post("/api/v1/analyze", json={"raw_case_text": ""}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_whitespace_only_returns_422(client):
    r = await client.post("/api/v1/analyze", json={"raw_case_text": "   \n\t  "}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_missing_field_returns_422(client):
    r = await client.post("/api/v1/analyze", json={}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_old_field_name_returns_422(client):
    """Sending case_text (old name) instead of raw_case_text must be rejected."""
    r = await client.post("/api/v1/analyze", json={"case_text": SAMPLE_CASE}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_invalid_json_body_returns_422(client):
    r = await client.post(
        "/api/v1/analyze",
        content=b"not-json",
        headers={**HEADERS_A, "Content-Type": "application/json"},
    )
    assert r.status_code == 422


async def test_extra_fields_are_ignored(client, mock_agents):
    async with client.stream(
        "POST",
        "/api/v1/analyze",
        json={"raw_case_text": SAMPLE_CASE, "unknown_field": "ignored"},
        headers=HEADERS_A,
    ) as resp:
        assert resp.status_code == 200


# ── Happy-path SSE structure ──────────────────────────────────────────────────


async def test_pipeline_returns_200_with_event_stream(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]


async def test_pipeline_emits_exactly_11_events(client, mock_agents):
    """5 steps × (running + completed) + 1 final done = 11 events."""
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert len(events) == 11


async def test_last_event_is_done(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    last = events[-1]
    assert last.get("step") == "done"
    assert last.get("status") == "completed"


async def test_final_event_contains_case_id(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert "case_id" in events[-1]


async def test_case_id_is_valid_uuid(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    uuid.UUID(events[-1]["case_id"])


async def test_completed_steps_arrive_in_correct_order(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    completed_steps = [
        e["step"] for e in events
        if e.get("status") == "completed" and e.get("step") != "done"
    ]
    assert completed_steps == EXPECTED_STEPS


async def test_running_event_precedes_completed_for_every_step(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    step_events = [e for e in events if "step" in e and e.get("step") != "done"]
    for name in EXPECTED_STEPS:
        pair = [e for e in step_events if e["step"] == name]
        assert len(pair) == 2, f"Expected 2 events for {name}, got {len(pair)}"
        assert pair[0]["status"] == "running"
        assert pair[1]["status"] == "completed"


async def test_step_indices_are_0_through_4(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    completed_indices = [
        e["step_index"] for e in events
        if e.get("status") == "completed" and "step_index" in e
    ]
    assert completed_indices == [0, 1, 2, 3, 4]


# ── Per-step result shape ─────────────────────────────────────────────────────


async def test_extraction_result_has_required_keys(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "extraction" and e.get("status") == "completed"
    )
    assert isinstance(data["core_facts"], list) and len(data["core_facts"]) > 0
    assert isinstance(data["entities"], list) and len(data["entities"]) > 0
    assert isinstance(data["chronological_timeline"], list) and len(data["chronological_timeline"]) > 0


async def test_rag_result_has_chunks_key(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "rag_retrieval" and e.get("status") == "completed"
    )
    assert "chunks" in data


async def test_strategy_result_has_required_keys(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "strategy" and e.get("status") == "completed"
    )
    for key in ["legal_issues", "applicable_laws", "arguments", "counterarguments", "legal_reasoning"]:
        assert key in data, f"Missing key: {key}"


async def test_drafting_result_has_brief_markdown(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "drafting" and e.get("status") == "completed"
    )
    assert "brief_markdown" in data
    assert isinstance(data["brief_markdown"], str) and len(data["brief_markdown"]) > 0


async def test_qa_result_has_required_keys(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "qa" and e.get("status") == "completed"
    )
    assert data["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert isinstance(data["hallucination_warnings"], list)


# ── Agent call counts ─────────────────────────────────────────────────────────


async def test_each_agent_called_exactly_once(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    mock_agents["extraction"].assert_called_once()
    mock_agents["rag"].assert_called_once()
    mock_agents["strategy"].assert_called_once()
    mock_agents["drafting"].assert_called_once()
    mock_agents["qa"].assert_called_once()


async def test_strategy_receives_extraction_output(client, mock_agents):
    from tests.conftest import MOCK_EXTRACTION
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    assert mock_agents["strategy"].call_args.args[0] == MOCK_EXTRACTION


async def test_drafting_receives_extraction_and_strategy(client, mock_agents):
    from tests.conftest import MOCK_EXTRACTION, MOCK_STRATEGY
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    assert mock_agents["drafting"].call_args.args[0] == MOCK_EXTRACTION
    assert mock_agents["drafting"].call_args.args[1] == MOCK_STRATEGY


# ── Error handling ────────────────────────────────────────────────────────────


async def test_extraction_failure_emits_error_event(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("OpenAI rate limit exceeded")
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    last = events[-1]
    assert last.get("event") == "error"
    assert "rate limit" in last.get("detail", "").lower()


async def test_mid_pipeline_failure_emits_completed_earlier_steps(client, mock_agents):
    mock_agents["strategy"].side_effect = RuntimeError("Strategy agent failed")
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    completed = {e["step"] for e in events if e.get("status") == "completed"}
    assert "extraction" in completed
    assert "rag_retrieval" in completed
    assert "strategy" not in completed


async def test_failure_last_event_is_error_not_done(client, mock_agents):
    mock_agents["qa"].side_effect = RuntimeError("QA failed")
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert events[-1].get("event") == "error"
    assert not any(e.get("step") == "done" for e in events)


async def test_failed_case_saved_with_failed_status(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("boom")
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    history = (await client.get("/api/v1/cases", headers=HEADERS_A)).json()
    assert len(history) == 1
    assert history[0]["status"] == "FAILED"


async def test_server_continues_serving_after_pipeline_error(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("boom")
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    mock_agents["extraction"].side_effect = None
    r = await client.get("/health")
    assert r.status_code == 200
