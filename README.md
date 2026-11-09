# LightRAG Model Context Protocol (MCP) Server

A lightweight, secure, and fully typed Model Context Protocol (MCP) server that acts as a proxy to an existing, online LightRAG REST service.

It covers LightRAG's **Query** and **Documents** endpoints, so LLM clients (such as Cursor, Claude Desktop, Claude Code, or standard IDE extensions) can both query your LightRAG knowledge base and manage the documents in it. Bulk-destructive operations are disabled unless you explicitly enable them.

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

- **Safe by Default**: Bulk-destructive admin tools (clear all documents, clear cache, force reset, cancel pipeline, repair conflicts) are hidden unless `LIGHTRAG_ENABLE_ADMIN_TOOLS=true`. Every tool carries MCP read-only / destructive hints.
- **Modern Stack**: Built with `fastmcp`, `pydantic` (v2), and `pydantic-settings`.
- **Fast Environment**: Managed natively using `uv`.
- **Three Query Modes**:
  - `query_text`: Standard retrieval and response generation. Automatically formats grounding references.
  - `query_data`: Returns structured knowledge graph data (entities, relationships, and metadata) as JSON.
  - `query_stream`: Connects to LightRAG's SSE stream and returns fully aggregated output (ideal for stdio-based transport client compatibility).
- **Document Management**: Upload files, insert text, track indexing, list, reprocess, and delete documents.

---

## Configuration

The server is configured via environment variables or a `.env` file:

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `LIGHTRAG_API_URL` | Base URL of the running LightRAG REST service | `http://localhost:9621` |
| `REQUEST_TIMEOUT` | Request timeout in seconds for communicating with LightRAG | `60.0` |
| `LIGHTRAG_ENABLE_ADMIN_TOOLS` | Expose the bulk-destructive admin tools listed below | `false` |

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

### Document Tools

Document tools return LightRAG's JSON response as-is. Ingestion is asynchronous: upload and insert tools return a `track_id` that you pass to `get_track_status` to see whether indexing finished or failed.

| Tool | Endpoint | Description |
| ---- | -------- | ----------- |
| `upload_document` | `POST /documents/upload` | Upload a local file by path and queue it for indexing |
| `insert_text` | `POST /documents/text` | Insert one text, with an optional source name and chunking strategy |
| `insert_texts` | `POST /documents/texts` | Insert several texts in one batch |
| `list_documents` | `POST /documents/paginated` | List documents with status filtering, paging, and sorting |
| `get_track_status` | `GET /documents/track_status/{track_id}` | Processing status and errors for an upload or insert |
| `get_status_counts` | `GET /documents/status_counts` | Number of documents per processing status |
| `get_pipeline_status` | `GET /documents/pipeline_status` | Current state of the indexing pipeline |
| `get_supported_file_types` | `GET /documents/supported_file_types` | File extensions accepted for upload |
| `scan_documents` | `POST /documents/scan` | Index new files found in LightRAG's input directory |
| `get_scan_status` | `GET /documents/scan/status/{track_id}` | Status of a scan job |
| `reprocess_failed_documents` | `POST /documents/reprocess_failed` | Requeue failed and pending documents |
| `delete_documents` | `DELETE /documents/delete_document` | Delete documents by ID (destructive) |
| `list_source_conflicts` | `GET /documents/source_conflicts` | Documents sharing the same canonical source |

**Admin tools** (only registered when `LIGHTRAG_ENABLE_ADMIN_TOOLS=true`):

| Tool | Endpoint | Description |
| ---- | -------- | ----------- |
| `clear_documents` | `DELETE /documents` | Delete **every** document and all graph data |
| `clear_cache` | `POST /documents/clear_cache` | Clear the LLM response cache |
| `force_reset_recovery` | `POST /documents/recovery/force_reset` | Clear the `recovery_required` fence after an interrupted job |
| `cancel_pipeline` | `POST /documents/cancel_pipeline` | Cancel the running indexing pipeline |
| `repair_source_conflict` | `POST /documents/source_conflicts/repair` | Keep one primary document for a conflicted source (dry run by default) |

#### Uploading files from Docker
`upload_document` reads the file on the machine running the MCP server. In Docker, mount the directories you want to upload from at the **same path** inside the container, read-only, so host paths work unchanged:
```bash
docker run -i --rm \
  -v "$HOME/Zotero/storage:$HOME/Zotero/storage:ro" \
  -e LIGHTRAG_API_URL="http://host.docker.internal:9621" \
  lightrag-mcp
```

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

3. **Updating Docker**:
  To update the service with a new revision, pull the latest code and rebuild the image under the same tag. There is no need to stop your LightRAG REST service, since building an image does not affect running containers:
```bash
git pull
docker build -t lightrag-mcp .
```
  Alternatively, stop any running `lightrag-mcp` containers first (they are removed automatically when started with `--rm`), then rebuild and clean up the old image. Stopping must come before the build, because the filter matches on the image tag, which moves to the new image once the build finishes:
```bash
docker ps -q --filter ancestor=lightrag-mcp | xargs -r docker stop
git pull
docker build -t lightrag-mcp .
docker image prune -f
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

### Claude Code CLI Configuration
Register the server with `claude mcp add`. Everything after `--` is the command Claude Code launches:

```bash
claude mcp add lightrag -- docker run -i --rm \
  -e LIGHTRAG_API_URL=http://host.docker.internal:9621 \
  lightrag-mcp
```

By default the server is added for the current project only. Use `-s user` to make it available in all your projects, or `-s project` to write a shareable `.mcp.json`:

```bash
claude mcp add -s user lightrag -- docker run -i --rm ...
```

Verify or remove it with:

```bash
claude mcp list            # shows connection status
claude mcp get lightrag    # shows the saved configuration
claude mcp remove lightrag
```

Inside a Claude Code session, `/mcp` also lists the server and its tools.

> **Linux:** `host.docker.internal` does not resolve by default. Add `--add-host=host.docker.internal:host-gateway` to the `docker run` arguments, or use `--network host` with `http://localhost:9621`.

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
