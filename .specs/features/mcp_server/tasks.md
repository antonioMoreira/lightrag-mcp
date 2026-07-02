# LightRAG Query MCP Server Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/mcp_server/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec — confirm before Execute. Guidelines found: none — strong defaults applied.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Configuration | unit | Env parsing, default values, validation | `tests/test_config.py` | `uv run pytest tests/test_config.py` |
| Client | unit / integration | Mocked HTTP requests to /query, /query/stream, /query/data, error handling | `tests/test_client.py` | `uv run pytest tests/test_client.py` |
| Server / Tools | unit / integration | Tool registration, parameter validation, proxying to client, output formatting | `tests/test_server.py` | `uv run pytest tests/test_server.py` |
| Deployment | none | Docker image build & run verification | `Dockerfile` | build gate only |

---

## Parallelism Assessment

> Generated from codebase — confirm before Execute.

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --------- | -------------- | --------------- | -------- |
| unit | Yes | Fully mocked HTTP client (`pytest-mock`), no shared files or mutable global states. | Written to use isolated client/mock fixtures per test |
| integration | Yes | Interfacing with local/mocked HTTP endpoint, isolated parameters | Mocked backend, no database modifications |

---

## Gate Check Commands

> Generated from codebase — confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | After tasks with unit tests only | `uv run pytest tests/` |
| Full | After tasks with integration tests | `uv run pytest tests/` |
| Build | After phase completion or config/entity-only tasks | `uv run pytest tests/ && docker build -t lightrag-mcp .` |

---

## Execution Plan

### Phase 1: Foundation (Sequential)
Establish the python workspace, dependencies, and configuration management.
```
T1 → T2 → T3
```

### Phase 2: Core Implementation (Parallel OK)
Implement the HTTP client and FastMCP server layers.
```
      ┌→ T4 [P] ─┐
T3 ───┤          ├──→ T6
      └→ T5 [P] ─┘
```

### Phase 3: Containerization & Integration (Sequential)
Create Dockerfile, run end-to-end local integration checks, and verify success criteria.
```
T6 → T7
```

---

## Task Breakdown

### T1: Initialize Python project and dependencies using `uv`
- **What**: Initialize the virtual environment and add all required runtime and development dependencies.
- **Where**: `pyproject.toml` (modify)
- **Depends on**: None
- **Reuses**: None
- **Requirement**: MCP-REQ-05
- **Tools**:
  - MCP: NONE
  - Skill: NONE
- **Done when**:
  - [ ] Running `uv add fastmcp httpx pydantic pydantic-settings` completes successfully.
  - [ ] Running `uv add --dev pytest pytest-asyncio pytest-mock` completes successfully.
  - [ ] `pyproject.toml` is populated with correct dependencies.
- **Tests**: none
- **Gate**: build

---

### T2: Configure project metadata and entry points
- **What**: Configure pyproject.toml scripts/entrypoints so that `lightrag-mcp` is executable via `uv run`.
- **Where**: `pyproject.toml` (modify)
- **Depends on**: T1
- **Reuses**: None
- **Requirement**: MCP-REQ-05, MCP-REQ-06
- **Tools**:
  - MCP: NONE
  - Skill: NONE
- **Done when**:
  - [ ] `[project.scripts]` section is added to `pyproject.toml` exposing `lightrag-mcp = "lightrag_mcp.server:main"`.
  - [ ] Project can compile/build without issues.
- **Tests**: none
- **Gate**: build

---

### T3: Implement Configuration Management
- **What**: Create configuration class utilizing Pydantic Settings to load env-controlled parameters like `LIGHTRAG_API_URL` and request timeout.
- **Where**: `src/lightrag_mcp/config.py`, `tests/test_config.py`
- **Depends on**: T2
- **Reuses**: None
- **Requirement**: MCP-REQ-04, MCP-REQ-05
- **Tools**:
  - MCP: NONE
  - Skill: NONE
- **Done when**:
  - [ ] `Settings` class created with default `LIGHTRAG_API_URL = "http://localhost:9621"`.
  - [ ] `tests/test_config.py` created to verify loading configuration from environment variables.
  - [ ] `uv run pytest tests/test_config.py` passes successfully.
- **Tests**: unit
- **Gate**: quick

---

### T4: Implement `LightRAGClient` [P]
- **What**: Create client class that handles async communication with the LightRAG REST server, mapping requests to Pydantic models.
- **Where**: `src/lightrag_mcp/client.py`, `tests/test_client.py`
- **Depends on**: T3
- **Reuses**: None
- **Requirement**: MCP-REQ-01, MCP-REQ-02, MCP-REQ-03, MCP-REQ-04
- **Tools**:
  - MCP: NONE
  - Skill: NONE
- **Done when**:
  - [ ] `LightRAGClient` is implemented with async methods `query_text`, `query_data`, and `query_stream`.
  - [ ] Requests/responses are validated using Pydantic models.
  - [ ] Connection/timeout error handling maps HTTP/network errors to descriptive custom exceptions.
  - [ ] `tests/test_client.py` created with mocks (`pytest-mock`) to verify happy path and error handling for all 3 query types.
  - [ ] `uv run pytest tests/test_client.py` passes successfully with at least 6 passing test cases.
- **Tests**: unit / integration
- **Gate**: quick

---

### T5: Implement `MCPServer` [P]
- **What**: Create FastMCP server registering the three query tools and mapping inputs correctly.
- **Where**: `src/lightrag_mcp/server.py`, `tests/test_server.py`
- **Depends on**: T3
- **Reuses**: None
- **Requirement**: MCP-REQ-01, MCP-REQ-02, MCP-REQ-03, MCP-REQ-06, MCP-REQ-07
- **Tools**:
  - MCP: NONE
  - Skill: NONE
- **Done when**:
  - [ ] FastMCP instance created and initialized with registered tools: `query_text`, `query_data`, `query_stream`.
  - [ ] Modern parameters validated using Pydantic parameters.
  - [ ] Tools delegate appropriately to `LightRAGClient` and return results formatted cleanly for MCP clients.
  - [ ] No database-modifying tools are defined (strictly read-only).
  - [ ] `tests/test_server.py` verifies tool execution with mocked client results.
  - [ ] `uv run pytest tests/test_server.py` passes successfully with at least 3 passing test cases.
- **Tests**: unit / integration
- **Gate**: quick

---

### T6: Configure Dockerfile and `.dockerignore`
- **What**: Create Dockerfile optimized for `uv` that builds a light image running the MCP server via stdio transport.
- **Where**: `Dockerfile`, `.dockerignore`
- **Depends on**: T4, T5
- **Reuses**: None
- **Requirement**: MCP-REQ-05
- **Tools**:
  - MCP: NONE
  - Skill: NONE
- **Done when**:
  - [ ] `.dockerignore` excludes unnecessary files (like `.git`, `.venv`, `__pycache__`).
  - [ ] `Dockerfile` copies `pyproject.toml`, installs dependencies with `uv sync --frozen --no-dev`, copies src, and sets the CMD to run the MCP server.
  - [ ] `docker build -t lightrag-mcp .` completes successfully.
- **Tests**: none
- **Gate**: build

---

### T7: Full Integration Testing & Verifier
- **What**: Perform end-to-end stdio execution verification and run the automated verifier.
- **Where**: `.specs/features/mcp_server/validation.md`
- **Depends on**: T6
- **Reuses**: None
- **Requirement**: MCP-REQ-01 to MCP-REQ-07
- **Tools**:
  - MCP: NONE
  - Skill: NONE
- **Done when**:
  - [ ] Stdio server run check is validated (starts, receives MCP initialize requests, and responds).
  - [ ] Verifier runs and outputs `.specs/features/mcp_server/validation.md` with PASS status for all criteria.
- **Tests**: unit / integration
- **Gate**: build

---

## Parallel Execution Map

Visual representation of task ordering within phases (`[P]` = order-free, no inter-task dependency):

```
Phase 1 (Sequential):
  T1 ──→ T2 ──→ T3

Phase 2 (Parallel):
  T3 complete, then:
    ├── T4 [P]  } Can run simultaneously
    └── T5 [P]  }

Phase 3 (Sequential):
  T4 and T5 complete, then:
    T6 ──→ T7
```

**Parallelism constraint:** A task marked `[P]` must have ALL of these:
- No unfinished dependencies.
- Required test type is parallel-safe (per the Parallelism Assessment).
- No shared mutable state with other `[P]` tasks in the same phase.

---

## Task Granularity Check

Before approving tasks, verify they are granular enough:

| Task                            | Scope         | Status       |
| ------------------------------- | ------------- | ------------ |
| T1: Initialize project & deps   | pyproject.toml | ✅ Granular  |
| T2: Configure entry points      | pyproject.toml | ✅ Granular  |
| T3: Implement config class      | 1 module      | ✅ Granular  |
| T4: Implement LightRAGClient    | 1 module      | ✅ Granular  |
| T5: Implement MCPServer         | 1 module      | ✅ Granular  |
| T6: Configure Dockerfile        | Docker files  | ✅ Granular  |
| T7: Integration & Verifier      | Test/Validate | ✅ Granular  |

**Granularity check**:
- ✅ 1 component / 1 function / 1 endpoint = Good
- ⚠️ 2-3 related things in same file = OK if cohesive
- ❌ Multiple components or files = MUST split

---

## Diagram-Definition Cross-Check

Before approving tasks, verify the execution diagram is consistent with the task definitions.

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1   | None                   | Start         | ✅ Match |
| T2   | T1                     | T1 → T2       | ✅ Match |
| T3   | T2                     | T2 → T3       | ✅ Match |
| T4   | T3                     | T3 → T4       | ✅ Match |
| T5   | T3                     | T3 → T5       | ✅ Match |
| T6   | T4, T5                 | T4, T5 → T6   | ✅ Match |
| T7   | T6                     | T6 → T7       | ✅ Match |

---

## Test Co-location Validation

Before approving tasks, verify EVERY task's `Tests` field is consistent with the Test Coverage Matrix.

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1   | Dependencies setup          | none            | none      | ✅ OK  |
| T2   | Project metadata setup      | none            | none      | ✅ OK  |
| T3   | Configuration               | unit            | unit      | ✅ OK  |
| T4   | Client                      | unit/integration| unit/integration | ✅ OK  |
| T5   | Server / Tools              | unit/integration| unit/integration | ✅ OK  |
| T6   | Deployment                  | none            | none      | ✅ OK  |
| T7   | Full verification           | none            | none      | ✅ OK  |
