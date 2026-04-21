"""
Quick smoke test for the Litigation Prep Assistant API.
Run with:  uv run python test_api.py

Make sure the server is already running in another terminal:
  uv run dev
"""

import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"

# ── Fake values standing in for teammates' work ──────────────────────────────

# Stands in for John's Clerk JWT — the stub auth dep reads this header
FAKE_USER_HEADER = {"x-user-id": "test-user-rithwik"}

# Stands in for a real case submitted through John's frontend form
SAMPLE_CASE = (
    "On 15 March 2023, John Kamau entered into a written agreement with Sarah Wanjiru "
    "for the sale of land parcel No. 123/456 in Kiambu County for KES 5,000,000. "
    "John paid a deposit of KES 500,000 and was given possession of the land. "
    "Sarah has since refused to execute the transfer documents and is claiming the "
    "agreement is void. John now seeks specific performance and damages."
)

# ── Helpers ──────────────────────────────────────────────────────────────────

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
BOLD = "\033[1m"
RESET = "\033[0m"

errors: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}" + (f"  →  {detail}" if detail else ""))
        errors.append(label)


def section(title: str) -> None:
    print(f"\n{BOLD}{'─' * 50}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")


# ── Tests ────────────────────────────────────────────────────────────────────

def test_health(client: httpx.Client) -> None:
    section("GET /health")
    r = client.get("/health")
    check("status 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check('body == {"status": "ok"}', body == {"status": "ok"}, str(body))


def test_me(client: httpx.Client) -> None:
    section("GET /me  (stub auth — stands in for John's Clerk JWT)")
    r = client.get("/me", headers=FAKE_USER_HEADER)
    check("status 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("user_id returned", body.get("user_id") == "test-user-rithwik", str(body))
    print(f"       user payload: {body}")


def test_history_empty(client: httpx.Client) -> None:
    section("GET /history  (should be empty for a fresh user)")
    r = client.get("/history", headers=FAKE_USER_HEADER)
    check("status 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("returns a list", isinstance(body, list), str(type(body)))
    print(f"       history items: {len(body)}")


def test_analyze_stream(client: httpx.Client) -> str | None:
    """
    Streams POST /analyze and validates every SSE event.
    Returns the analysis_id from the final 'complete' event.

    This stands in for John's frontend AgentStepViewer which will consume
    these same events and render them step by step.
    Amit's RAG retrieval will appear at step_index 1 — currently returns [].
    """
    section("POST /analyze  (full SSE pipeline)")
    print(f"  case text: \"{SAMPLE_CASE[:80]}...\"")
    print()

    seen_steps: list[str] = []
    analysis_id: str | None = None

    expected_steps = ["extraction", "rag_retrieval", "strategy", "drafting", "qa"]

    with client.stream(
        "POST",
        "/analyze",
        headers={**FAKE_USER_HEADER, "Content-Type": "application/json"},
        content=json.dumps({"case_text": SAMPLE_CASE}),
        timeout=120,
    ) as response:
        check("status 200", response.status_code == 200, str(response.status_code))

        for raw_line in response.iter_lines():
            if not raw_line.startswith("data:"):
                continue

            payload = json.loads(raw_line[len("data:"):].strip())

            if payload.get("event") == "complete":
                analysis_id = payload.get("analysis_id")
                print(f"  {PASS}  complete  →  analysis_id: {analysis_id}")
                break

            if payload.get("event") == "error":
                print(f"  {FAIL}  pipeline error: {payload.get('detail')}")
                errors.append("pipeline returned error event")
                break

            step = payload.get("step", "")
            status = payload.get("status", "")

            if status == "running":
                print(f"  ···  {step:<15} running...")
            elif status == "done":
                result = payload.get("result", {})
                seen_steps.append(step)

                # Step-specific spot checks
                if step == "extraction":
                    facts = result.get("facts", [])
                    entities = result.get("entities", [])
                    timeline = result.get("timeline", [])
                    check(
                        f"extraction: facts, entities, timeline present",
                        bool(facts) and bool(entities) and bool(timeline),
                        f"facts={len(facts)} entities={len(entities)} timeline={len(timeline)}",
                    )

                elif step == "rag_retrieval":
                    # Amit's stub — just check the key exists
                    check(
                        "rag_retrieval: chunks key present  (Amit's stub returns [])",
                        "chunks" in result,
                        str(result),
                    )

                elif step == "strategy":
                    check(
                        "strategy: legal_issues + applicable_laws present",
                        bool(result.get("legal_issues")) and bool(result.get("applicable_laws")),
                        str(list(result.keys())),
                    )

                elif step == "drafting":
                    brief = result.get("brief", {})
                    check(
                        "drafting: brief has all 5 fields",
                        all(k in brief for k in ["facts", "issues", "arguments", "counterarguments", "conclusion"]),
                        str(list(brief.keys())),
                    )

                elif step == "qa":
                    check(
                        "qa: is_grounded + risk_level present",
                        "is_grounded" in result and "risk_level" in result,
                        str(list(result.keys())),
                    )
                    print(f"       grounded={result.get('is_grounded')}  risk={result.get('risk_level')}")

    check(
        "all 5 steps completed in order",
        seen_steps == expected_steps,
        f"got {seen_steps}",
    )
    return analysis_id


def test_history_after_analyze(client: httpx.Client, analysis_id: str) -> None:
    section("GET /history  (should have 1 item now)")
    r = client.get("/history", headers=FAKE_USER_HEADER)
    check("status 200", r.status_code == 200)
    items = r.json()
    check("at least 1 item in history", len(items) >= 1, f"got {len(items)}")
    if items:
        latest = items[0]
        check("latest item status is 'completed'", latest.get("status") == "completed", str(latest.get("status")))
        print(f"       latest case id : {latest.get('id')}")
        print(f"       latest status  : {latest.get('status')}")


def test_history_detail(client: httpx.Client, analysis_id: str) -> None:
    section(f"GET /history/{{analysis_id}}  (full result with agent steps)")
    r = client.get(f"/history/{analysis_id}", headers=FAKE_USER_HEADER)
    check("status 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    steps = body.get("steps", [])
    check("5 agent steps stored in DB", len(steps) == 5, f"got {len(steps)}")
    step_names = [s["step_name"] for s in steps]
    check(
        "step names correct",
        step_names == ["extraction", "rag_retrieval", "strategy", "drafting", "qa"],
        str(step_names),
    )
    check("all steps status=done", all(s["status"] == "done" for s in steps))
    check("all steps have result JSON", all(s["result"] is not None for s in steps))


def test_history_not_found(client: httpx.Client) -> None:
    section("GET /history/nonexistent-id  (should 404)")
    r = client.get("/history/does-not-exist", headers=FAKE_USER_HEADER)
    check("status 404", r.status_code == 404, str(r.status_code))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{BOLD}Litigation Prep Assistant — API smoke tests{RESET}")
    print(f"Target: {BASE}\n")

    try:
        with httpx.Client(base_url=BASE) as client:
            test_health(client)
            test_me(client)
            test_history_empty(client)
            analysis_id = test_analyze_stream(client)
            if analysis_id:
                test_history_after_analyze(client, analysis_id)
                test_history_detail(client, analysis_id)
            test_history_not_found(client)
    except httpx.ConnectError:
        print(f"\n{FAIL}  Cannot connect to {BASE}")
        print("     Make sure the server is running:  uv run dev\n")
        sys.exit(1)

    print(f"\n{'─' * 50}")
    if errors:
        print(f"{FAIL}  {len(errors)} check(s) failed:")
        for e in errors:
            print(f"     • {e}")
        sys.exit(1)
    else:
        print(f"{PASS}  All checks passed.")
    print()


if __name__ == "__main__":
    main()
