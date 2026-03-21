# Quickstart: Insights Block Navigation and Live Updates

**Branch**: `014-insights-scroll-autoupdate`

## Prerequisites

```bash
git checkout 014-insights-scroll-autoupdate
./script/bootstrap
```

## Start dev server

```bash
./script/server
# → http://localhost:8080  (debug@example.com / password)
```

## Test the features

**P1 — Block click navigation:**
1. Upload a `.note` file with multiple pages (or use an existing processed note).
2. Open the file viewer and wait for the Insights panel to show AI summaries.
3. Click any segment card that shows page references (e.g., "p.3, 4").
4. Verify the page viewer scrolls smoothly to the referenced page.

**P2 — Live processing updates:**
1. Upload a new `.note` file.
2. Immediately open the file viewer — the Insights panel should show a processing indicator.
3. Wait (without refreshing) — the panel should populate automatically when done.

## Run tests

```bash
./script/test
# or targeted:
python -m pytest tests/server/routes/test_extended.py -v
```

## Run type check and lint

```bash
./script/lint
./script/run-mypy.sh
```

## Key files

| File | Role |
|------|------|
| `supernote/server/static/js/components/SummaryPanel.js` | P1 click handler + P2 polling + processing indicator |
| `supernote/server/static/js/components/FileViewer.js` | P1 navigate-to-page event listener + scroll |
| `supernote/server/routes/extended.py` | Backend: optional `file_id` query param on tasks endpoint |
| `tests/server/routes/test_extended.py` | Backend tests for the query param change |

## Relevant existing code

- `SummaryPanel.js:127–145` — existing scroll methods (`scrollAiToPage`, `scrollOcrToPage`)
- `SummaryPanel.js:219–238` — AI segment template (add click handler here)
- `FileViewer.js:123–147` — IntersectionObserver (reference for page DOM structure)
- `FileViewer.js:268` — SummaryPanel integration (add event listener here)
- `supernote/server/routes/extended.py:74–101` — existing tasks route handler
