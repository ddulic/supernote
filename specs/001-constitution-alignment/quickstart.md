# Quickstart: Validating Constitution Alignment

This guide lets you verify each user story independently after implementation.

## US1 — Type Safety: Zero mypy errors

```bash
# Run the full type check — should exit 0 with no output
./script/run-mypy.sh

# Verify no Optional[T] remains in server or models
grep -r "Optional\[" supernote/server/ supernote/models/ --include="*.py"
# Expected: no output

# Verify notebook/ and cli/ are no longer excluded
grep "supernote/notebook\|supernote/cli" pyproject.toml
# Expected: no exclude entries for these paths
```

---

## US2 — Security: Quota enforcement

```bash
# Start ephemeral server (sets default quota from config)
supernote serve --ephemeral

# In another terminal, log in
supernote cloud login --url http://127.0.0.1:8080 debug@example.com --password password

# Set a tiny quota for the debug user (via admin CLI)
supernote admin user set-quota debug@example.com --bytes 1024

# Attempt to upload a file larger than 1 KB — should be rejected
supernote cloud upload tests/testdata/20251207_221454.note
# Expected: quota exceeded error before upload begins
```

---

## US2 — Security: Temp file TTL cleanup

```bash
# Start ephemeral server with a short cleanup interval for testing
SUPERNOTE_TEMP_CLEANUP_INTERVAL=5 SUPERNOTE_TEMP_TTL=10 supernote serve --ephemeral

# Manually place a fake chunk file older than 10 seconds in the blob store
touch -d "60 seconds ago" /tmp/supernote-test-storage/user_data/test.note.part.1

# Wait 10 seconds, then check that the file is gone
sleep 15
ls /tmp/supernote-test-storage/user_data/test.note.part.1
# Expected: No such file or directory
```

---

## US3 — Code hygiene: No note content in trace logs

```bash
# Start server with trace logging enabled
SUPERNOTE_TRACE_LOG=/tmp/supernote-trace.json supernote serve --ephemeral

# Upload a test note and trigger processing (OCR/synthesis)
supernote cloud login --url http://127.0.0.1:8080 debug@example.com --password password
supernote cloud upload tests/testdata/20251207_221454.note

# Wait for processing, then inspect the trace log
cat /tmp/supernote-trace.json | python3 -c "
import sys, json
data = [json.loads(l) for l in sys.stdin if l.strip()]
for entry in data:
    body = entry.get('response', {}).get('body', '')
    if isinstance(body, str) and len(body) > 100:
        print('POTENTIAL LEAK:', entry['request']['url'][:80])
"
# Expected: no output (all large response bodies are redacted)
```

---

## Full test suite

```bash
./script/test
# Expected: all 300+ tests pass, zero failures
```
