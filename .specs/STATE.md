# STATE

## Decisions

### AD-001
- **Decision**: Use `uv` strictly for dependency management and execution in this workspace.
- **Reason**: The user specifically requested to use `uv` and its ecosystem commands (`uv add`, `uv run`).
- **Trade-off**: Requires environments that support `uv` (standard on modern Python configurations).
- **Scope**: Entire project dependency and runtime management.
- **Date**: 2026-07-02
- **Status**: active

### AD-002
- **Decision**: Use `fastmcp` as the framework for building the MCP server, proxying requests to the running LightRAG REST API.
- **Reason**: FastMCP is a modern, high-level framework for building MCP servers, and the user's LightRAG instance is already online at `http://localhost:9621/` with queries strictly read-only.
- **Trade-off**: Requires external service communication and handling network-related errors gracefully.
- **Scope**: MCP Server framework and transport architecture.
- **Date**: 2026-07-02
- **Status**: active

### AD-003
- **Decision**: Use `pydantic` (v2) for all data models, request/response validation, and serialization.
- **Reason**: The user preferred modern tools like Pydantic over TypedDict for cleaner validation and serialization.
- **Trade-off**: Slightly higher runtime overhead than TypedDict, but negligible and offset by robust validation.
- **Scope**: All data transfer objects and client-server payloads.
- **Date**: 2026-07-02
- **Status**: active

## Handoff

- **Feature**: `.specs/features/mcp_server/spec.md`
- **Phase / Task**: Execution Phase / Final Verification
- **Completed**: All tasks (T1 to T7) are fully implemented, tested, and validated.
- **In-progress**: None
- **Next step**: Expose the Docker image or run the MCP server locally with standard clients.
- **Blockers**: None
- **Uncommitted files**: None
- **Branch**: main
