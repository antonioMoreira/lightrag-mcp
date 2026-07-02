# LightRAG Query MCP Server Design

**Spec**: `.specs/features/mcp_server/spec.md`
**Status**: Approved (by user context)

---

## Architecture Overview

The MCP server is a standalone containerized service using `fastmcp` to expose LightRAG query tools. Rather than running the heavy LightRAG models internally, it acts as a lightweight client proxy that communicates asynchronously with the running LightRAG REST service at `http://localhost:9621` using `httpx`.

```mermaid
graph TD
    Client[MCP Client (e.g. Claude Desktop)] <== Stdio / JSON-RPC ==> Server[fastmcp Server]
    Server -- Async HTTP (httpx) --> LightRAG[LightRAG REST API http://localhost:9621]
    LightRAG -- Query Response --> Server
```

---

## Code Reuse Analysis

### Existing Components to Leverage
This is a brand-new project workspace `/home/antonio/Documents/Python/lightrag-mcp`. We will build the components from scratch.
However, we will reuse the exact schemas from the running LightRAG API to construct our Pydantic models.

### Integration Points

| System         | Integration Method                      |
| -------------- | --------------------------------------- |
| LightRAG API | Async HTTP POST to `/query`, `/query/stream`, and `/query/data` |

---

## Components

### 1. `LightRAGClient`
- **Purpose**: Low-level client responsible for making HTTP requests to LightRAG and parsing responses into Pydantic models.
- **Location**: `src/lightrag_mcp/client.py`
- **Interfaces**:
  - `async def query_text(request: QueryRequest) -> QueryResponse`
  - `async def query_data(request: QueryRequest) -> QueryDataResponse`
  - `async def query_stream(request: QueryRequest) -> AsyncGenerator[str, None]`
- **Dependencies**: `httpx`, `pydantic`, `pydantic_settings`
- **Reuses**: None

### 2. `MCPServer`
- **Purpose**: Exposes the FastMCP server instance and registers the query tools.
- **Location**: `src/lightrag_mcp/server.py`
- **Interfaces**:
  - `query_text(...)` -> Tool exposed to MCP clients
  - `query_data(...)` -> Tool exposed to MCP clients
  - `query_stream(...)` -> Tool exposed to MCP clients
- **Dependencies**: `fastmcp`, `LightRAGClient`
- **Reuses**: None

---

## Data Models

All models are implemented using `pydantic` (v2) for strict runtime verification.

### `QueryRequest` (Inputs)
Matches the `/query` endpoint input format.
```python
from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Optional, Any

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="The query text")
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = Field(
        default="mix", description="Query mode"
    )
    only_need_context: Optional[bool] = Field(None, description="If True, only returns context")
    only_need_prompt: Optional[bool] = Field(None, description="If True, only returns prompt")
    response_type: Optional[str] = Field(None, description="Defines the response format (e.g. 'Bullet Points')")
    top_k: Optional[int] = Field(None, ge=1, description="Number of top items to retrieve")
    chunk_top_k: Optional[int] = Field(None, ge=1, description="Number of text chunks to retrieve")
    max_entity_tokens: Optional[int] = Field(None, ge=1, description="Max entity tokens")
    max_relation_tokens: Optional[int] = Field(None, ge=1, description="Max relation tokens")
    max_total_tokens: Optional[int] = Field(None, ge=1, description="Max total tokens budget")
    hl_keywords: Optional[List[str]] = Field(None, description="High-level keywords")
    ll_keywords: Optional[List[str]] = Field(None, description="Low-level keywords")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Chat history")
    user_prompt: Optional[str] = Field(None, description="User customized prompt instructions")
    enable_rerank: Optional[bool] = Field(None, description="Enable reranking")
    include_references: Optional[bool] = Field(True, description="Include reference list")
    include_chunk_content: Optional[bool] = Field(False, description="Include actual chunk content")
    stream: Optional[bool] = Field(None, description="Stream output flag")
```

### `ReferenceItem` & `QueryResponse` (Outputs)
```python
class ReferenceItem(BaseModel):
    reference_id: str
    file_path: str
    content: Optional[List[str]] = None

class QueryResponse(BaseModel):
    response: str
    references: Optional[List[ReferenceItem]] = None
```

### `QueryDataResponse` (Outputs)
```python
class QueryDataResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
```

---

## Error Handling Strategy

| Error Scenario | Handling      | User Impact      |
| -------------- | ------------- | ---------------- |
| Connection Refused (LightRAG offline) | Catch `httpx.RequestError`, log it, and return a clean MCP user-facing error message with troubleshooting tips. | "Unable to reach the LightRAG service at http://localhost:9621. Is it running?" |
| Pydantic Validation Error (Client-side) | fastmcp / pydantic raises validation error on type mismatch before reaching LightRAG. | Returns structured parameter error response to MCP client. |
| HTTP 4xx/5xx from LightRAG | Catch non-200 responses, parse error details from response body if possible, and return a clean tool error. | "LightRAG service returned error: [details]" |
| Timeout | Configure a sensible default timeout (e.g. 60 seconds) in `httpx`. Catch timeout errors. | "Query timed out. The RAG service took too long to respond." |

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| ------- | -------------------- | ------ | ---------- |
| Connection URLs in Docker | `src/lightrag_mcp/config.py` | If running inside Docker, `localhost` resolves to the container itself, meaning the MCP server won't reach LightRAG at `localhost:9621` on the host. | Define a `LIGHTRAG_API_URL` environment variable via Pydantic Settings. Default to `http://localhost:9621` but allow setting to `http://host.docker.internal:9621` or a Docker bridge IP/alias. |
| Streaming over Stdio | `src/lightrag_mcp/server.py` | FastMCP stdio transport doesn't support streaming back raw tokens natively to all clients seamlessly. | For `query_stream`, we will consume the stream asynchronously using `httpx` and accumulate the full text before returning, while also supporting standard query to guarantee maximum compatibility. |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Packaging Tool | `uv` | Mandated by user. Extremely fast dependency resolution, lockfile creation, and script execution. |
| Client Lib | `httpx` | Offers native async capabilities, support for streaming response bodies, and clean API compared to `urllib` or `requests`. |
| Settings Management | `pydantic-settings` | Modern, standard way to handle configuration via system environment variables. |
