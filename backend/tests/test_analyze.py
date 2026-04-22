"""
Tests for POST /api/v1/analyze — the core SSE pipeline.

SSE event shape reference:
  Section:  {"type": "markdown_section", "section_id": str, "heading": str, "markdown": str}
  Final:    {"type": "complete", "case_id": str}
  Error:    {"type": "error", "detail": str}
"""

import uuid

import pytest

from tests.conftest import ANALYZE_FORM_BODY, HEADERS_A, SAMPLE_CASE, collect_sse, run_analyze

EXPECTED_SECTION_IDS = [
    "extraction",
    "rag_retrieval",
    "strategy",
    "drafting",
    "qa",
]


def _markdown_sections(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("type") == "markdown_section"]


# ── Input validation ──────────────────────────────────────────────────────────


async def test_blank_title_returns_422(client):
    r = await client.post(
        "/api/v1/analyze",
        data={"title": "", "case_text": SAMPLE_CASE},
        headers=HEADERS_A,
    )
    assert r.status_code == 422


async def test_whitespace_title_returns_422(client):
    r = await client.post(
        "/api/v1/analyze",
        data={"title": "  \t ", "case_text": SAMPLE_CASE},
        headers=HEADERS_A,
    )
    assert r.status_code == 422


async def test_missing_title_returns_422(client):
    r = await client.post("/api/v1/analyze", data={"case_text": SAMPLE_CASE}, headers=HEADERS_A)
    assert r.status_code == 422


async def test_no_case_text_and_no_file_returns_422(client):
    r = await client.post(
        "/api/v1/analyze",
        data={"title": "Matter only", "case_text": ""},
        headers=HEADERS_A,
    )
    assert r.status_code == 422


async def test_whitespace_only_case_text_returns_422(client):
    r = await client.post(
        "/api/v1/analyze",
        data={"title": "Matter X", "case_text": "   \n\t  "},
        headers=HEADERS_A,
    )
    assert r.status_code == 422


async def test_json_body_instead_of_form_returns_422(client):
    """Analyze expects application/x-www-form-urlencoded or multipart (Form fields)."""
    r = await client.post(
        "/api/v1/analyze",
        json={"title": "X", "case_text": SAMPLE_CASE},
        headers=HEADERS_A,
    )
    assert r.status_code == 422


async def test_invalid_body_returns_422(client):
    r = await client.post(
        "/api/v1/analyze",
        content=b"not-form",
        headers={**HEADERS_A, "Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 422


async def test_extra_form_fields_are_ignored(client, mock_agents):
    async with client.stream(
        "POST",
        "/api/v1/analyze",
        data={**ANALYZE_FORM_BODY, "unknown_field": "ignored"},
        headers=HEADERS_A,
    ) as resp:
        assert resp.status_code == 200


# ── Happy-path SSE structure ──────────────────────────────────────────────────


async def test_pipeline_returns_200_with_event_stream(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]


async def test_pipeline_emits_five_markdown_sections_plus_complete(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert len(events) == 6
    assert len(_markdown_sections(events)) == 5
    assert events[-1].get("type") == "complete"


async def test_last_event_is_complete(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    last = events[-1]
    assert last.get("type") == "complete"
    assert "case_id" in last


async def test_final_event_contains_case_id(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert "case_id" in events[-1]


async def test_case_id_is_valid_uuid(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    uuid.UUID(events[-1]["case_id"])


async def test_markdown_sections_arrive_in_correct_order(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    section_ids = [e["section_id"] for e in _markdown_sections(events)]
    assert section_ids == EXPECTED_SECTION_IDS


async def test_each_markdown_section_has_heading_and_body(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    for e in _markdown_sections(events):
        assert isinstance(e.get("heading"), str) and len(e["heading"]) > 0
        assert isinstance(e.get("markdown"), str) and len(e["markdown"]) > 0


async def test_section_indices_match_step_order(client, mock_agents):
    """section_id order aligns with pipeline step indices 0–4."""
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    for i, e in enumerate(_markdown_sections(events)):
        assert EXPECTED_SECTION_IDS[i] == e["section_id"]


# ── Per-step Markdown content ─────────────────────────────────────────────────


async def test_extraction_markdown_contains_structure(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    ext = next(e for e in _markdown_sections(events) if e["section_id"] == "extraction")
    md = ext["markdown"]
    assert "### Core facts" in md
    assert "### Entities" in md
    assert "John Kamau" in md


async def test_rag_markdown_when_empty_chunks(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    rag = next(e for e in _markdown_sections(events) if e["section_id"] == "rag_retrieval")
    assert "No precedents" in rag["markdown"]


async def test_strategy_markdown_contains_issues_and_laws(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    strat = next(e for e in _markdown_sections(events) if e["section_id"] == "strategy")
    md = strat["markdown"]
    assert "### Legal issues" in md
    assert "### Applicable laws" in md
    assert "Law of Contract Act" in md


async def test_strategy_counterarguments_are_structured_objects(client, mock_agents):
    """Each counterargument must be a dict with rebutting_argument and counterargument keys."""
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "strategy" and e.get("status") == "completed"
    )
    assert isinstance(data["counterarguments"], list)
    for item in data["counterarguments"]:
        assert isinstance(item, dict), "Each counterargument must be a dict"
        assert "rebutting_argument" in item, "Missing rebutting_argument key"
        assert "counterargument" in item, "Missing counterargument key"
        assert isinstance(item["rebutting_argument"], str) and item["rebutting_argument"]
        assert isinstance(item["counterargument"], str) and item["counterargument"]


async def test_strategy_arguments_are_structured_objects(client, mock_agents):
    """Each argument must be a dict with issue, applicable_kenyan_law, and argument_summary."""
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "strategy" and e.get("status") == "completed"
    )
    assert isinstance(data["arguments"], list) and len(data["arguments"]) > 0
    for arg in data["arguments"]:
        assert isinstance(arg, dict)
        for key in ["issue", "applicable_kenyan_law", "argument_summary"]:
            assert key in arg, f"Argument missing key: {key}"


async def test_drafting_result_has_brief_markdown(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    draft = next(e for e in _markdown_sections(events) if e["section_id"] == "drafting")
    assert "# IN THE MATTER OF" in draft["markdown"]


async def test_drafting_brief_contains_required_sections(client, mock_agents):
    """The brief must include all sections mandated by the improved drafting prompt."""
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "drafting" and e.get("status") == "completed"
    )
    brief = data["brief_markdown"]
    for section in [
        "## FACTS",
        "## ISSUES FOR DETERMINATION",
        "## LEGAL ARGUMENTS",
        "## RESPONDENT'S ANTICIPATED POSITION",
        "## CONCLUSION AND PRAYER FOR RELIEF",
    ]:
        assert section in brief, f"Brief missing required section: {section}"


async def test_qa_result_has_required_keys(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    qa = next(e for e in _markdown_sections(events) if e["section_id"] == "qa")
    assert "LOW" in qa["markdown"]


async def test_qa_result_has_all_output_fields(client, mock_agents):
    """QA result must include all four fields defined by the improved QA prompt schema."""
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "qa" and e.get("status") == "completed"
    )
    for key in ["risk_level", "hallucination_warnings", "missing_logic", "risk_notes"]:
        assert key in data, f"QA result missing key: {key}"
    assert isinstance(data["missing_logic"], list)
    assert isinstance(data["risk_notes"], list)


async def test_extraction_entities_have_name_type_role(client, mock_agents):
    """Every entity extracted must have name, type, and role per the improved extraction prompt."""
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "extraction" and e.get("status") == "completed"
    )
    for entity in data["entities"]:
        assert isinstance(entity, dict)
        for field in ["name", "type", "role"]:
            assert field in entity, f"Entity missing field: {field}"
            assert isinstance(entity[field], str) and entity[field]


async def test_extraction_timeline_events_have_date_and_event(client, mock_agents):
    """Every timeline entry must have date and event keys."""
    async with client.stream(
        "POST", "/api/v1/analyze", json={"raw_case_text": SAMPLE_CASE}, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    data = next(
        e["data"] for e in events if e.get("step") == "extraction" and e.get("status") == "completed"
    )
    for entry in data["chronological_timeline"]:
        assert isinstance(entry, dict)
        assert "date" in entry and isinstance(entry["date"], str) and entry["date"]
        assert "event" in entry and isinstance(entry["event"], str) and entry["event"]


# ── Agent call counts ─────────────────────────────────────────────────────────


async def test_each_agent_called_exactly_once(client, mock_agents):
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
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
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    assert mock_agents["strategy"].call_args.args[0] == MOCK_EXTRACTION


async def test_drafting_receives_extraction_and_strategy(client, mock_agents):
    from tests.conftest import MOCK_EXTRACTION, MOCK_STRATEGY

    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    assert mock_agents["drafting"].call_args.args[0] == MOCK_EXTRACTION
    assert mock_agents["drafting"].call_args.args[1] == MOCK_STRATEGY


# ── Error handling ────────────────────────────────────────────────────────────


async def test_extraction_failure_emits_error_event(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("OpenAI rate limit exceeded")
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    last = events[-1]
    assert last.get("type") == "error"
    assert "rate limit" in last.get("detail", "").lower()


async def test_mid_pipeline_failure_emits_markdown_for_prior_steps_only(client, mock_agents):
    mock_agents["strategy"].side_effect = RuntimeError("Strategy agent failed")
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    section_ids = [e["section_id"] for e in _markdown_sections(events)]
    assert section_ids == ["extraction", "rag_retrieval"]


async def test_failure_last_event_is_error_not_complete(client, mock_agents):
    mock_agents["qa"].side_effect = RuntimeError("QA failed")
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        events = await collect_sse(resp)
    assert events[-1].get("type") == "error"
    assert not any(e.get("type") == "complete" for e in events)


async def test_failed_case_saved_with_failed_status(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("boom")
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    history = (await client.get("/api/v1/cases", headers=HEADERS_A)).json()
    assert len(history) == 1
    assert history[0]["status"] == "FAILED"


async def test_server_continues_serving_after_pipeline_error(client, mock_agents):
    mock_agents["extraction"].side_effect = RuntimeError("boom")
    async with client.stream(
        "POST", "/api/v1/analyze", data=ANALYZE_FORM_BODY, headers=HEADERS_A
    ) as resp:
        await collect_sse(resp)
    mock_agents["extraction"].side_effect = None
    r = await client.get("/health")
    assert r.status_code == 200
