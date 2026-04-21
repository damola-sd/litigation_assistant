from collections.abc import Generator
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


def _stream_steps() -> Generator[str, None, None]:
    # TODO: wire orchestrator and persist case state.
    steps = [
        {"agent": "Extraction", "status": "completed"},
        {"agent": "Strategy", "status": "completed"},
        {"agent": "Drafting", "status": "completed"},
        {"agent": "QA", "status": "completed"},
    ]
    for step in steps:
        yield f"event: step\ndata: {json.dumps(step)}\n\n"
    yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"


@router.post("/analyze")
def analyze() -> StreamingResponse:
    return StreamingResponse(_stream_steps(), media_type="text/event-stream")
