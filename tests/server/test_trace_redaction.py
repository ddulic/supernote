"""T029: Test that summary/insights route responses are redacted in the trace log.

The trace middleware should replace the response body with
"<note-content redacted>" for routes that return sensitive note content
(e.g. /api/extended/transcript, /api/file/query/summary/id).
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.test_utils import TestClient


@pytest.fixture
def mock_trace_log(tmp_path: Path) -> str:
    """Enable trace log for this module."""
    log_file = tmp_path / "trace_redaction.log"
    return str(log_file)


async def test_transcript_response_body_is_redacted_in_trace(
    client: TestClient,
    auth_headers: dict[str, str],
    create_test_user: None,
    mock_trace_log: str,
) -> None:
    """T029: The response body from /api/extended/transcript should appear as
    '<note-content redacted>' in the trace log rather than the actual content."""

    sensitive_transcript = "This is highly sensitive handwritten note content."

    # Mock the search service to return a known transcript without hitting AI or DB
    with patch(
        "supernote.server.services.search.SearchService.get_transcript",
        new=AsyncMock(return_value=sensitive_transcript),
    ):
        # The transcript route also resolves user_id from user_service — mock that too
        with patch(
            "supernote.server.services.user.UserService.get_user_id",
            new=AsyncMock(return_value=1),
        ):
            resp = await client.post(
                "/api/extended/transcript",
                # Use camelCase alias as required by the DTO
                json={"fileId": 12345},
                headers=auth_headers,
            )

    assert resp.status == 200
    resp_json = await resp.json()
    # The actual HTTP response should still contain the real content
    assert resp_json.get("transcript") == sensitive_transcript

    # Now check the trace log — the response body should be redacted
    log_path = Path(mock_trace_log)
    assert log_path.exists(), "Trace log file should have been created"

    content = log_path.read_text().strip()
    entry = json.loads(content)

    assert "response" in entry
    logged_body = entry["response"]["body"]

    assert logged_body == "<note-content redacted>", (
        f"Expected trace log to contain '<note-content redacted>' but got: {logged_body!r}"
    )


async def test_summary_by_id_response_body_is_redacted_in_trace(
    client: TestClient,
    auth_headers: dict[str, str],
    create_test_user: None,
    mock_trace_log: str,
) -> None:
    """T029: The response body from /api/file/query/summary/id should appear as
    '<note-content redacted>' in the trace log."""
    from supernote.models.summary import SummaryItem

    # Build a proper SummaryItem DTO (the type that list_summaries_by_id returns)
    fake_summary = SummaryItem(
        id=1,
        content="Sensitive summary content from a note",
        data_source="TEST",
    )

    with patch(
        "supernote.server.services.summary.SummaryService.list_summaries_by_id",
        new=AsyncMock(return_value=[fake_summary]),
    ):
        resp = await client.post(
            "/api/file/query/summary/id",
            json={"ids": [1]},
            headers=auth_headers,
        )

    assert resp.status == 200
    resp_json = await resp.json()
    # The actual HTTP response should still have real content
    # The VO uses alias "summaryDOList"
    summaries = resp_json.get("summaryDOList", [])
    assert len(summaries) == 1
    assert summaries[0].get("content") == "Sensitive summary content from a note"

    # The trace log response body must be redacted
    log_path = Path(mock_trace_log)
    assert log_path.exists(), "Trace log file should have been created"

    # The file uses indent=2, so entries span multiple lines — parse all objects
    raw = log_path.read_text().strip()

    entries: list[dict[str, object]] = []
    depth = 0
    current: list[str] = []
    for line in raw.splitlines():
        current.append(line)
        depth += line.count("{") - line.count("}")
        if depth == 0 and current:
            try:
                entries.append(json.loads("\n".join(current)))
            except json.JSONDecodeError:
                pass
            current = []

    assert entries, "Trace log should contain at least one entry"

    # Find the entry for the summary/id request
    summary_entry = next(
        (
            e
            for e in entries
            if "/api/file/query/summary/id" in str(e.get("request", {}).get("url", ""))  # type: ignore[attr-defined]
        ),
        None,
    )
    assert summary_entry is not None, (
        "No trace entry found for /api/file/query/summary/id"
    )

    logged_body = summary_entry["response"]["body"]  # type: ignore[index]
    assert logged_body == "<note-content redacted>", (
        f"Expected trace log to contain '<note-content redacted>' but got: {logged_body!r}"
    )
