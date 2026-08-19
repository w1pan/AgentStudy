# AgentStudy Reliability and Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the reviewed runtime, upload-security, concurrency, dependency, history-persistence, and timing defects while adding regression coverage.

**Architecture:** Keep the existing Vue/FastAPI split. Make backend integrations lazy so imports stay side-effect free, let FastAPI run blocking SDK work in worker threads, generate OSS object keys on the server, and keep frontend conversation/timing state in Pinia with browser persistence. Use Python `unittest` and Vitest for regression tests.

**Tech Stack:** Python 3.14, FastAPI, LangChain/LangGraph, Qdrant, Alibaba OSS, Vue 3, Pinia, TypeScript, Vitest.

---

### Task 1: Backend message history and lazy runtime resources

**Files:**
- Create: `agent-learning/tests/test_personal_chief.py`
- Modify: `agent-learning/app/agents/personal_chief.py`

- [ ] **Step 1: Write failing message serialization and sync-stream tests**

```python
import inspect
import unittest
from langchain_core.messages import AIMessage, HumanMessage
from app.agents import personal_chief


class PersonalChiefTests(unittest.TestCase):
    def test_serialize_messages_supports_human_and_ai_messages(self):
        result = personal_chief._serialize_messages([
            HumanMessage(content="hello"),
            AIMessage(content="hi"),
        ])
        self.assertEqual(result, [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ])

    def test_search_recipes_is_a_sync_generator(self):
        self.assertTrue(inspect.isgeneratorfunction(personal_chief.search_recipes))
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/Scripts/python.exe -m unittest tests.test_personal_chief -v`

Expected: failure because `_serialize_messages` is missing and `search_recipes` is an async generator.

- [ ] **Step 3: Implement lazy model, search, and checkpoint resources**

Import `AIMessage`; replace import-time `exit`, model, Tavily, and SQLite creation with `_get_model()`, `_get_tavily()`, and `_get_checkpointer()` cached functions. Create the database parent directory before opening SQLite. Add `_serialize_messages()` and make `get_messages()` call it. Change `search_recipes` to a synchronous generator so `StreamingResponse` iterates it in Starlette's worker thread.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv/Scripts/python.exe -m unittest tests.test_personal_chief -v`

Expected: both tests pass without requiring API credentials during import.

### Task 2: Backend request validation and bounded OSS upload

**Files:**
- Create: `agent-learning/tests/test_oss.py`
- Create: `agent-learning/tests/test_schemas.py`
- Modify: `agent-learning/app/api/v1/oss.py`
- Modify: `agent-learning/app/models/schemas.py`

- [ ] **Step 1: Write failing object-key and validation tests**

```python
import unittest
from pydantic import ValidationError
from app.api.v1.oss import _build_object_key
from app.models.schemas import RetrieveRequest


class OssTests(unittest.TestCase):
    def test_object_key_ignores_client_path_and_is_unique(self):
        first, content_type = _build_object_key("../../photo.png")
        second, _ = _build_object_key("../../photo.png")
        self.assertRegex(first, r"^uploads/[0-9a-f]{32}\.png$")
        self.assertNotEqual(first, second)
        self.assertEqual(content_type, "image/png")

    def test_rejects_non_image_extension(self):
        with self.assertRaises(ValueError):
            _build_object_key("payload.exe")

    def test_upload_rejects_actual_body_larger_than_ten_mebibytes(self):
        response = self.client.post(
            "/oss/upload",
            params={"filename": "photo.png"},
            content=b"x" * (10 * 1024 * 1024 + 1),
            headers={"Content-Type": "image/png"},
        )
        self.assertEqual(response.status_code, 413)


class SchemaTests(unittest.TestCase):
    def test_top_k_is_bounded(self):
        with self.assertRaises(ValidationError):
            RetrieveRequest(query="food", top_k=1000)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/Scripts/python.exe -m unittest tests.test_oss tests.test_schemas -v`

Expected: `_build_object_key` is missing and `top_k=1000` is accepted.

- [ ] **Step 3: Implement server-owned keys, bounded proxy upload, and Pydantic bounds**

Generate `uploads/{uuid4().hex}{suffix}` from an allowlist of JPEG, PNG, GIF, and WebP extensions. Stream the request body through FastAPI, reject the actual byte stream above 10 MiB, verify the request MIME matches the extension, then upload to OSS in a worker thread with overwrite forbidden. Validate `OSS_BUCKET`, URL-encode the returned access path, add per-field source bounds, and enforce `1 <= top_k <= 20` plus the same thread-ID constraint on POST/GET/DELETE routes.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv/Scripts/python.exe -m unittest tests.test_oss tests.test_schemas -v`

Expected: all tests pass.

### Task 3: FastAPI lifecycle and blocking boundaries

**Files:**
- Create: `agent-learning/tests/test_api_shape.py`
- Modify: `agent-learning/app/main.py`
- Modify: `agent-learning/app/api/v1/chat.py`

- [ ] **Step 1: Write failing endpoint-shape test**

```python
import inspect
import unittest
from app.api.v1.chat import retrieve_endpoint


class ApiShapeTests(unittest.TestCase):
    def test_retrieve_endpoint_is_sync_for_threadpool_execution(self):
        self.assertFalse(inspect.iscoroutinefunction(retrieve_endpoint))
```

- [ ] **Step 2: Run test and verify RED**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_shape -v`

Expected: failure because `retrieve_endpoint` is currently async while doing synchronous SDK work.

- [ ] **Step 3: Move startup work into lifespan and blocking endpoints into worker threads**

Make `retrieve_endpoint` and `chat_endpoint` normal `def` functions. Add a FastAPI lifespan context that calls `ensure_collection_initialized` through `asyncio.to_thread` rather than during module import. Configure explicit CORS origins from `CORS_ORIGINS`, defaulting to local Vite development origins.

- [ ] **Step 4: Run test and verify GREEN**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_shape -v`

Expected: pass and importing `app.main` performs no embedding/network call.

### Task 4: Frontend timing, thread persistence, and image validation

**Files:**
- Create: `Agent/src/stores/__tests__/chat.spec.ts`
- Modify: `Agent/src/stores/chat.ts`
- Modify: `Agent/src/components/ChatInterface.vue`

- [ ] **Step 1: Write failing Pinia tests**

Mock `retrieveRecipes`, `streamChat`, and OSS calls. Assert that `queryTimeMs` equals the backend `query_time_ms`, that the generated thread ID is stored in `localStorage`, that a second store instance restores it, and that resetting chat stores a new ID. Add a test that rejects non-image or over-10-MiB files before requesting an upload URL.

- [ ] **Step 2: Run tests and verify RED**

Run: `npm.cmd run test:unit -- --run src/stores/__tests__/chat.spec.ts`

Expected: failures because query time and persisted thread state do not exist and image validation is missing.

- [ ] **Step 3: Implement store-owned timing and persistent thread state**

Add `queryTimeMs`, `THREAD_ID_STORAGE_KEY`, `loadOrCreateThreadId()`, `persistThreadId()`, and `validateImageFile()`. Save `retrieveResponse.query_time_ms`; reset it for each request and reset. Reject unsupported images and images over 10 MiB before uploading, and block sends while history hydration is pending.

- [ ] **Step 4: Update the component**

Use `onMounted(chatStore.loadHistory)`, bind `SourcesPanel` to `chatStore.queryTimeMs`, remove the full-request performance timer, and revoke object preview URLs when replaced, removed, or unmounted.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `npm.cmd run test:unit -- --run src/stores/__tests__/chat.spec.ts`

Expected: all new tests pass.

### Task 5: Reproducible dependencies and documentation

**Files:**
- Modify: `agent-learning/pyproject.toml`
- Modify: `agent-learning/requirements.txt`
- Modify: `agent-learning/README.md`
- Modify: `Agent/README.md`
- Modify: `README.md`

- [ ] **Step 1: Consolidate backend dependencies**

Add direct runtime dependencies for `python-dotenv`, `qdrant-client`, and `uvicorn[standard]` to `pyproject.toml`. Replace duplicated `requirements.txt` pins with `-e .` so `pyproject.toml` is the source of truth.

- [ ] **Step 2: Replace template documentation**

Document the monorepo layout, required `DASHSCOPE_*`, `TAVILY_API_KEY`, and OSS variables, backend and frontend start commands, local CORS configuration, and the fact that runtime databases and `.env` files are intentionally untracked.

- [ ] **Step 3: Verify manifests and docs**

Run: `.venv/Scripts/python.exe -m compileall -q app tests`

Expected: exit 0.

### Task 6: Full verification and review

**Files:**
- Review all modified files.

- [ ] **Step 1: Run backend suite**

Run: `.venv/Scripts/python.exe -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 2: Run frontend suite and static checks**

Run: `npm.cmd run test:unit -- --run`

Run: `npm.cmd run type-check`

Run: `npm.cmd run build`

Run: `node_modules/.bin/eslint.cmd .`

Run: `node_modules/.bin/oxlint.cmd .`

Expected: all commands exit 0 with no warnings or errors.

- [ ] **Step 3: Inspect Git state and request code review**

Run: `git status --short` and `git diff --check`.

Expected: only intentional source, test, plan, manifest, and documentation changes; no secrets, databases, build output, or whitespace errors.
