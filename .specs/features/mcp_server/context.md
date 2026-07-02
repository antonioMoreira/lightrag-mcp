# LightRAG Query MCP Server Context

**Gathered:** 2026-07-02
**Spec:** `.specs/features/mcp_server/spec.md`
**Status:** Ready for design

---

## Feature Boundary

This feature implements a pure, read-only MCP server (using FastMCP and Pydantic) that acts as a proxy client to an already-running LightRAG REST server at `http://localhost:9621/`.

---

## Implementation Decisions

### Running Instance Integration
- The LightRAG REST service is already online at `http://localhost:9621/` (running in a container named `lightrag-lightrag-1`).
- The MCP server will communicate directly with this REST API.
- The base URL is configurable via an environment variable `LIGHTRAG_API_URL` to allow flexibility (such as container-to-container communication inside a Docker network, e.g. `http://lightrag-lightrag-1:9621` or `http://host.docker.internal:9621`).

### Query-Only Constraint
- ONLY query endpoints will be exposed:
  - `POST /query` -> Exposed as tool `query_text`
  - `POST /query/stream` -> Exposed as tool `query_stream` (yielding or returning aggregated text)
  - `POST /query/data` -> Exposed as tool `query_data`
- It is **strictly prohibited** to modify the database (no insert, scan, upload, delete, edit entity, edit relation, or clear cache endpoints shall be exposed).

### Implementation Technologies
- **Dependency Management**: Use `uv` strictly (`uv add` for dependencies, `uv run` for execution).
- **Type Safety**: Prefer modern tools; utilize `pydantic` (v2) models for request/response serialization instead of simple `TypedDict`.
- **Server Framework**: Use `fastmcp` to build the MCP server.
- **Containerization**: Provide a proper, optimized `Dockerfile` configured to run with `uv`.

### Transport Mode
- Run primarily as a standard MCP stdio server inside the container, facilitating easy execution via `docker run -i` in desktop environments (like Claude Desktop).

---

## Specific References
- LightRAG REST API Swagger: `http://localhost:9621/docs` or `http://localhost:9621/redoc#tag/query`
- Container Name: `lightrag-lightrag-1`

---

## Deferred Ideas
- Document upload or scanning tools (strictly deferred as per current read-only requirements).
