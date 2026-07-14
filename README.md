# LightRAG Model Context Protocol (MCP) Server

A lightweight, secure, and fully typed Model Context Protocol (MCP) server that acts as a query proxy to an existing, online LightRAG REST service. 

This server is strictly **read-only** (it does not support document ingestion, indexing, or database modifications) and is designed to bridge LLM clients (such as Cursor, Claude Desktop, or standard IDE extensions) with your LightRAG knowledge base.

---

## Architecture Overview

The MCP server operates over standard I/O (stdio) transport to bridge your AI clients with the LightRAG REST service.

```
+------------+               +------------------+               +------------------+
| MCP Client | <--- Stdio -> | LightRAG MCP     | <-- HTTP/JS -> | LightRAG Service |
| (Cursor)   |               | Server (FastMCP) |               | (localhost:9621) |
+------------+               +------------------+               +------------------+
```

---

## Key Features

- **Strictly Read-Only**: Completely prohibits database modification to guarantee storage safety.
- **Modern Stack**: Built with `fastmcp`, `pydantic` (v2), and `pydantic-settings`.
- **Fast Environment**: Managed natively using `uv`.
- **Three Query Modes**:
  - `query_text`: Standard retrieval and response generation. Automatically formats grounding references.
  - `query_data`: Returns structured knowledge graph data (entities, relationships, and metadata) as JSON.
  - `query_stream`: Connects to LightRAG's SSE stream and returns fully aggregated output (ideal for stdio-based transport client compatibility).

---

## Configuration

The server is configured via environment variables or a `.env` file:

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `LIGHTRAG_API_URL` | Base URL of the running LightRAG REST service | `http://localhost:9621` |
| `REQUEST_TIMEOUT` | Request timeout in seconds for communicating with LightRAG | `60.0` |

---

## Exposed MCP Tools

All tools validate their inputs using Pydantic. Any validation errors are caught and returned gracefully to the client.

### 1. `query_text`
Queries standard text response from LightRAG.
- **Parameters**:
  - `query` (str, required): Prompt or question (minimum 3 characters).
  - `mode` (string, optional): Search mode (`local`, `global`, `hybrid`, `naive`, `mix`, `bypass`). Default: `mix`.
  - `include_references` (bool, optional): Append source context files to the end of the text response. Default: `true`.
  - `include_chunk_content` (bool, optional): Include actual raw content of referenced chunks. Default: `false`.
  - Additional optional constraints: `top_k`, `chunk_top_k`, `max_total_tokens`, `only_need_context`, etc.

### 2. `query_data`
Queries structured knowledge graph data (entities, relationships, and metadata).
- **Parameters**: Same as above (except reference options). Returns a rich JSON payload.

### 3. `query_stream`
Queries streaming response chunks from LightRAG, accumulating the response internally, and returning the fully assembled text.
- **Parameters**: Same as `query_data`.

---

## Getting Started

### Option A: Running with Docker (Recommended)

1. **Build the Image**:
```bash
docker build -t lightrag-mcp .
```

2. **Run the Container**:
  Since the server uses standard input/output (`stdio`) to communicate, make sure to run it interactively (`-i`). If your LightRAG REST service runs on the host network, point the URL to `host.docker.internal`:
```bash
docker run -i --rm \
  -e LIGHTRAG_API_URL="http://host.docker.internal:9621" \
  lightrag-mcp
```

### Option B: Running Locally

1. Ensure you have `uv` installed.
2. Run the entrypoint directly:
   ```bash
   LIGHTRAG_API_URL="http://localhost:9621" uv run lightrag-mcp
   ```

---

## Integration with MCP Clients

### Claude Desktop Configuration
Add the following snippet to your `claude_desktop_config.json` (typically found in `~/.config/Claude/claude_desktop_config.json` on Linux or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "lightrag": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "LIGHTRAG_API_URL=http://host.docker.internal:9621",
        "lightrag-mcp"
      ]
    }
  }
}
```

---

## Development & Testing

### Running Tests
To run the automated configuration, client, and tool validation tests:
```bash
uv run pytest tests/
```

### Formatting and Linting
This project conforms strictly to standard Python patterns. You can check types and formatting via:
```bash
uv run mypy src/
```
