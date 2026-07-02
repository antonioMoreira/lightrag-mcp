# LightRAG Query MCP Server Specification

## Problem Statement

Users of LightRAG need a secure, containerized Model Context Protocol (MCP) server to query an existing, online LightRAG instance. The MCP server acts as a clean, type-safe query bridge between MCP-compliant clients (e.g., Claude Desktop, IDE extensions) and the LightRAG REST service without directly modifying or managing the underlying storage or database.

## Goals

- [ ] Provide an MCP server built with `fastmcp` that connects to a LightRAG REST API (default `http://localhost:9621`).
- [ ] Expose query capabilities (Text Query, Streaming Query, and Struct Data Query) as type-safe tools using `pydantic`.
- [ ] Containerize the MCP server using a well-configured `Dockerfile` utilizing `uv` for lightning-fast and reliable environment setup.
- [ ] Ensure strict read-only guarantees; modifying the knowledge graph or database is completely prohibited.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature     | Reason         |
| ----------- | -------------- |
| Write tools | User specified that modifying the database is strictly prohibited. No document uploads, entity creations, or graph updates are allowed. |
| In-container LightRAG | The MCP server acts as a client/proxy to an external/sibling LightRAG API. It does not run LightRAG locally. |
| Authentication | Current REST endpoint does not require credentials for queries. The MCP server runs in local/stdio trusted mode. |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here — nothing is left silently unclear.

| Assumption / decision | Chosen default  | Rationale | Confirmed? |
| --------------------- | --------------- | --------- | ---------- |
| Base API URL | Default to `http://localhost:9621` or env `LIGHTRAG_API_URL` | Allows containerized networking where localhost might resolve to the container itself (e.g. use `http://host.docker.internal:9621` on Mac/Windows, or container name on custom Docker network). | Yes (by context) |
| Streaming tool behavior | Read-only accumulation for Stdio | MCP stdio transport doesn't support raw streaming natively unless chunked. The tool will collect stream chunks and return the final aggregated text, or we'll provide standard query. | Yes |
| FastMCP framework version | Standard stable FastMCP | Uses `fastmcp` package recommended by Anthropic. | Yes |

---

## User Stories

### P1: Query Text ⭐ MVP

**User Story**: As an AI Assistant client, I want to query the LightRAG knowledge graph in a selected mode (local, global, hybrid, naive, mix, bypass) and get a summarized textual response with references so that I can provide highly accurate answers to the user.

**Why P1**: This is the core purpose of a RAG query tool.

**Acceptance Criteria**:
1. WHEN the `query_text` tool is called with a prompt string, THEN the system SHALL validate the input and forward it to `POST /query`.
2. WHEN forwarding the request, THEN the system SHALL default to `mix` mode unless a custom mode is supplied.
3. WHEN the LightRAG server responds with standard JSON, THEN the system SHALL parse the response into a Pydantic model (`QueryResponse`) and return the answer as plain text/markdown.
4. WHEN the `include_references` or `include_chunk_content` parameters are set, THEN the system SHALL configure the payload accordingly.

**Independent Test**: Can invoke the `query_text` tool via FastMCP inspect/CLI with a query "What is LightRAG?" and see a formatted text answer.

---

### P1: Query Data ⭐ MVP

**User Story**: As a developer client, I want to retrieve structured knowledge graph data (entities, relationships, chunks, and references) for a query so that I can inspect or visualize the retrieved knowledge subgraph.

**Why P1**: Allows programmatic clients to access structured subgraph details directly via `/query/data`.

**Acceptance Criteria**:
1. WHEN the `query_data` tool is called, THEN the system SHALL validate input and forward the query to `POST /query/data`.
2. WHEN the LightRAG server returns structured subgraph elements, THEN the system SHALL parse them using a Pydantic model (`QueryDataResponse`) and output the structured JSON.

**Independent Test**: Can invoke the `query_data` tool and receive a JSON payload with `status`, `message`, `data` (entities, relations, chunks, references), and `metadata` fields.

---

### P2: Query Text Stream

**User Story**: As an assistant, I want to query LightRAG using a streaming connection so that I can process the token chunks dynamically.

**Why P2**: Enhances user experience by reducing perceived latency.

**Acceptance Criteria**:
1. WHEN the `query_stream` tool is called, THEN the system SHALL make an async streaming request to `POST /query/stream`.
2. THE system SHALL accumulate the text chunks in real-time and return the aggregated response (or yield intermediate chunks if the MCP client supports streaming tools).

**Independent Test**: Can invoke the `query_stream` tool and verify it completes successfully and returns the fully assembled text response.

---

## Edge Cases

- WHEN the LightRAG REST server is offline or unreachable THEN the MCP server SHALL return a clear, graceful error message instead of crashing.
- WHEN invalid modes (not in `local`, `global`, `hybrid`, `naive`, `mix`, `bypass`) are provided, THEN the system SHALL raise a Pydantic validation error before making any network requests.
- WHEN the query text is too short (e.g. <3 characters) THEN Pydantic validation SHALL reject it immediately.

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story       | Phase  | Status  |
| -------------- | ----------- | ------ | ------- |
| MCP-REQ-01      | P1: Query Text | Design | Pending |
| MCP-REQ-02      | P1: Query Data | Design | Pending |
| MCP-REQ-03      | P2: Query Stream | Design | Pending |
| MCP-REQ-04      | Edge cases & Errors | Design | Pending |
| MCP-REQ-05      | Docker & uv Setup | Design | Pending |
| MCP-REQ-06      | FastMCP Configuration | Design | Pending |
| MCP-REQ-07      | Strict Read-Only Policy | Design | Pending |

**Coverage**: 7 total, 7 mapped to tasks, 0 unmapped

---

## Success Criteria

How we know the feature is successful:
- [ ] FastMCP server starts successfully via command line and Docker container.
- [ ] Tools `query_text`, `query_data`, and `query_stream` are discoverable by any standard MCP client.
- [ ] A query returns grounded knowledge from the running LightRAG REST instance within <10 seconds.
