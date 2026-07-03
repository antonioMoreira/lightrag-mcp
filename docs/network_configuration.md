# Docker Networking & Connection Configuration

This guide provides detailed instructions on how to configure connectivity between the **LightRAG MCP Server** container and the underlying **LightRAG REST API** across different operating systems and deployment models.

---

## The Network Isolation Challenge

When the LightRAG MCP server runs inside a Docker container (or is spawned by an IDE or application like Claude Desktop running via Docker), `localhost` inside the container refers to the **container's own network namespace**, not your computer. Because the LightRAG REST service runs externally, the MCP container cannot connect to it using `localhost:9621`.

We solve this cleanly using Pydantic Settings to override the `LIGHTRAG_API_URL` environment variable depending on your environment.

---

## Connection Scenarios

### Scenario A: Running Both Locally (No Containers)
If both the LightRAG REST API and the MCP server are running directly on your host machine:
- **API URL**: `http://localhost:9621` (default)
- **Command**:
  ```bash
  uv run lightrag-mcp
  ```

---

### Scenario B: Containerized MCP Server to Host REST API
If your LightRAG REST service is running on your host machine (or mapped to port `9621` on your host), and the MCP server runs in a container:

#### 1. On macOS and Windows
Docker Desktop automatically maps the DNS name `host.docker.internal` to resolve to the host machine.
- **API URL**: `http://host.docker.internal:9621`
- **Command**:
  ```bash
  docker run -i --rm \
    -e LIGHTRAG_API_URL="http://host.docker.internal:9621" \
    lightrag-mcp
  ```

#### 2. On Linux
On Linux hosts, `host.docker.internal` is **not** defined inside containers by default. You must explicitly register the host gateway route using the `--add-host` flag:
- **API URL**: `http://host.docker.internal:9621`
- **Command**:
  ```bash
  docker run -i --rm \
    --add-host=host.docker.internal:host-gateway \
    -e LIGHTRAG_API_URL="http://host.docker.internal:9621" \
    lightrag-mcp
  ```

---

### Scenario C: Sibling Containers (Shared Docker Network)
If the LightRAG REST API is running inside another Docker container (e.g. named `lightrag-lightrag-1` as part of a docker-compose deployment) and you want them to communicate:

1. **Identify or Create the Network**:
   Find the network your LightRAG container is running on:
   ```bash
   docker inspect lightrag-lightrag-1 --format='{{json .NetworkSettings.Networks}}'
   ```
   *(Let's assume the network is named `lightrag-network`)*.

2. **Connect the MCP Container to the same Network**:
   Run the MCP server container on that network. You can now use the sibling container's name directly as the host:
   - **API URL**: `http://lightrag-lightrag-1:9621`
   - **Command**:
     ```bash
     docker run -i --rm \
       --network="lightrag-network" \
       -e LIGHTRAG_API_URL="http://lightrag-lightrag-1:9621" \
       lightrag-mcp
     ```

---

## Integration Examples

### 1. Claude Desktop (macOS/Windows)
Add this to your `claude_desktop_config.json`:
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

### 2. Claude Desktop (Linux)
Include the `--add-host` argument so the container can resolve `host.docker.internal`:
```json
{
  "mcpServers": {
    "lightrag": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--add-host=host.docker.internal:host-gateway",
        "-e",
        "LIGHTRAG_API_URL=http://host.docker.internal:9621",
        "lightrag-mcp"
      ]
    }
  }
}
```
