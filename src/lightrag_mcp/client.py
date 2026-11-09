import json
import mimetypes
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

# --- Pydantic Data Models ---

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=65536, description="The query text")
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = Field(
        default="mix", description="Query mode"
    )
    only_need_context: bool | None = Field(None, description="If True, only returns context")
    only_need_prompt: bool | None = Field(None, description="If True, only returns prompt")
    response_type: str | None = Field(
        None, min_length=1, max_length=256, description="Defines the response format (e.g. 'Bullet Points')"
    )
    top_k: int | None = Field(None, ge=1, le=1000, description="Number of top items to retrieve")
    chunk_top_k: int | None = Field(None, ge=1, le=1000, description="Number of text chunks to retrieve")
    max_entity_tokens: int | None = Field(None, ge=1, le=1000000, description="Max entity tokens")
    max_relation_tokens: int | None = Field(None, ge=1, le=1000000, description="Max relation tokens")
    max_total_tokens: int | None = Field(None, ge=1, le=1000000, description="Max total tokens budget")
    hl_keywords: list[str] | None = Field(None, max_length=64, description="High-level keywords")
    ll_keywords: list[str] | None = Field(None, max_length=64, description="Low-level keywords")
    conversation_history: list[dict[str, Any]] | None = Field(None, description="Chat history")
    user_prompt: str | None = Field(None, max_length=65536, description="User customized prompt instructions")
    disable_user_prompt_prefix: bool | None = Field(
        None,
        description="If True, the server-side global prompt prefix is not prepended to user_prompt"
    )
    enable_rerank: bool | None = Field(None, description="Enable reranking")
    include_references: bool | None = Field(True, description="Include reference list")
    include_chunk_content: bool | None = Field(False, description="Include actual chunk content")
    include_progress: bool | None = Field(
        None,
        description="If True, emits retrieval pipeline progress events before response chunks in /query/stream"
    )
    stream: bool | None = Field(None, description="Stream output flag")

class ReferenceItem(BaseModel):
    reference_id: str
    file_path: str
    content: list[str] | None = None

class QueryResponse(BaseModel):
    response: str
    references: list[ReferenceItem] | None = None
    response_time: float | None = None
    llm_generated: bool = True

class QueryDataResponse(BaseModel):
    status: str
    message: str
    data: dict[str, Any]
    metadata: dict[str, Any]

DocStatus = Literal["pending", "parsing", "analyzing", "processing", "preprocessed", "processed", "failed"]

class TextChunkingConfig(BaseModel):
    strategy: Literal[
        "fixed_token", "recursive_character", "semantic_vector", "paragraph_semantic", "custom"
    ] = Field(default="fixed_token", description="Chunking strategy")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")

class InsertTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The text to insert")
    file_source: str | None = Field(None, description="Source name recorded for citations")
    chunking: TextChunkingConfig | None = Field(None, description="Chunking configuration")

class InsertTextsRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="The texts to insert")
    file_sources: list[str] | None = Field(None, description="Source names, one per text")
    chunking: TextChunkingConfig | None = Field(None, description="Chunking configuration")

class DocumentsRequest(BaseModel):
    status_filters: list[DocStatus] | None = Field(None, description="Filter by document statuses")
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=50, ge=10, le=200, description="Documents per page")
    sort_field: Literal["created_at", "updated_at", "id", "file_path"] = Field(
        default="updated_at", description="Field to sort by"
    )
    sort_direction: Literal["asc", "desc"] = Field(default="desc", description="Sort direction")

class DeleteDocRequest(BaseModel):
    doc_ids: list[str] = Field(..., min_length=1, description="IDs of the documents to delete")
    delete_file: bool = Field(default=False, description="Also delete the file in the input directory")
    delete_llm_cache: bool = Field(default=False, description="Also delete cached LLM extraction results")

class SourceConflictRepairRequest(BaseModel):
    canonical_source_key: str = Field(..., min_length=1, description="Canonical source key to repair")
    primary_doc_id: str = Field(..., min_length=1, description="Document ID to keep as the single primary")
    expected_candidate_count: int | None = Field(None, ge=0, description="CAS token from the dry run")
    expected_candidate_fingerprint: str | None = Field(None, description="CAS token from the dry run")
    dry_run: bool = Field(default=True, description="Report only instead of committing")

# --- Custom Exception ---

class LightRAGClientError(Exception):
    """Exception raised for errors in the LightRAG client."""

# --- Client Implementation ---

class LightRAGClient:
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def query_text(self, request: QueryRequest) -> QueryResponse:
        """Query standard text response from LightRAG."""
        url = f"{self.base_url}/query"
        payload = request.model_dump(exclude_none=True)
        
        # Ensure stream is False for standard query
        payload["stream"] = False

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise LightRAGClientError(
                        f"LightRAG server returned error status {response.status_code}: {response.text}"
                    )
                data = response.json()
                return QueryResponse.model_validate(data)
            except LightRAGClientError:
                raise
            except httpx.RequestError as e:
                raise LightRAGClientError(f"HTTP connection error: {e}") from e
            except Exception as e:
                raise LightRAGClientError(f"Failed to process response: {e}") from e

    async def query_data(self, request: QueryRequest) -> QueryDataResponse:
        """Query structured knowledge graph data from LightRAG."""
        url = f"{self.base_url}/query/data"
        payload = request.model_dump(exclude_none=True)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise LightRAGClientError(
                        f"LightRAG server returned error status {response.status_code}: {response.text}"
                    )
                data = response.json()
                return QueryDataResponse.model_validate(data)
            except LightRAGClientError:
                raise
            except httpx.RequestError as e:
                raise LightRAGClientError(f"HTTP connection error: {e}") from e
            except Exception as e:
                raise LightRAGClientError(f"Failed to process response: {e}") from e

    async def query_stream(self, request: QueryRequest) -> AsyncGenerator[str]:
        """Query streaming response chunks from LightRAG (NDJSON / SSE)."""
        url = f"{self.base_url}/query/stream"
        payload = request.model_dump(exclude_none=True)
        
        # Ensure stream is True for streaming query
        payload["stream"] = True

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        # Consume body for detail
                        err_text = await response.aread()
                        raise LightRAGClientError(
                            f"LightRAG server returned error status {response.status_code}: {err_text.decode()}"
                        )
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        # Strip SSE prefixes if present (e.g. "data: ")
                        cleaned = line.removeprefix("data: ")
                        try:
                            parsed = json.loads(cleaned)
                        except json.JSONDecodeError:
                            yield cleaned
                            continue

                        if isinstance(parsed, dict):
                            if parsed.get("error"):
                                raise LightRAGClientError(
                                    f"LightRAG stream error: {parsed['error']}"
                                )
                            chunk = parsed.get("response")
                            if isinstance(chunk, str) and chunk:
                                yield chunk
                        else:
                            yield cleaned
            except LightRAGClientError:
                raise
            except httpx.RequestError as e:
                raise LightRAGClientError(f"HTTP connection error: {e}") from e
            except Exception as e:
                raise LightRAGClientError(f"Failed to stream response: {e}") from e

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Send a request to a LightRAG endpoint and return the decoded JSON body."""
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code != 200:
                    raise LightRAGClientError(
                        f"LightRAG server returned error status {response.status_code}: {response.text}"
                    )
                return response.json()
            except LightRAGClientError:
                raise
            except httpx.RequestError as e:
                raise LightRAGClientError(f"HTTP connection error: {e}") from e
            except Exception as e:
                raise LightRAGClientError(f"Failed to process response: {e}") from e

    async def upload_document(self, file_path: str) -> dict[str, Any]:
        """Upload a local file to the LightRAG input directory and queue it for indexing."""
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise LightRAGClientError(f"File not found or not readable by the MCP server: {path}")

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            data = path.read_bytes()
        except OSError as e:
            raise LightRAGClientError(f"Failed to read file {path}: {e}") from e

        files = {"file": (path.name, data, content_type)}
        return await self._request_json("POST", "/documents/upload", files=files)

    async def insert_text(self, request: InsertTextRequest) -> dict[str, Any]:
        """Insert a single text into LightRAG."""
        return await self._request_json("POST", "/documents/text", json=request.model_dump(exclude_none=True))

    async def insert_texts(self, request: InsertTextsRequest) -> dict[str, Any]:
        """Insert multiple texts into LightRAG."""
        return await self._request_json("POST", "/documents/texts", json=request.model_dump(exclude_none=True))

    async def list_documents(self, request: DocumentsRequest) -> dict[str, Any]:
        """List documents with pagination, status filtering and sorting."""
        return await self._request_json(
            "POST", "/documents/paginated", json=request.model_dump(exclude_none=True)
        )

    async def get_track_status(self, track_id: str) -> dict[str, Any]:
        """Get the processing status of documents created by an upload or insert."""
        return await self._request_json("GET", f"/documents/track_status/{track_id}")

    async def get_status_counts(self) -> dict[str, Any]:
        """Get the number of documents in each processing status."""
        return await self._request_json("GET", "/documents/status_counts")

    async def get_pipeline_status(self) -> dict[str, Any]:
        """Get the current state of the indexing pipeline."""
        return await self._request_json("GET", "/documents/pipeline_status")

    async def get_supported_file_types(self) -> dict[str, Any]:
        """Get the file extensions accepted for upload."""
        return await self._request_json("GET", "/documents/supported_file_types")

    async def scan_documents(self) -> dict[str, Any]:
        """Scan the LightRAG input directory for new documents."""
        return await self._request_json("POST", "/documents/scan")

    async def get_scan_status(self, track_id: str) -> dict[str, Any]:
        """Get the status of a scan job."""
        return await self._request_json("GET", f"/documents/scan/status/{track_id}")

    async def reprocess_failed(self) -> dict[str, Any]:
        """Requeue failed and pending documents for processing."""
        return await self._request_json("POST", "/documents/reprocess_failed")

    async def delete_documents(self, request: DeleteDocRequest) -> dict[str, Any]:
        """Delete documents and all their associated data by ID."""
        return await self._request_json(
            "DELETE", "/documents/delete_document", json=request.model_dump()
        )

    async def list_source_conflicts(self, limit: int = 50, cursor: str | None = None) -> dict[str, Any]:
        """List documents that share the same canonical source."""
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return await self._request_json("GET", "/documents/source_conflicts", params=params)

    async def repair_source_conflict(self, request: SourceConflictRepairRequest) -> dict[str, Any]:
        """Resolve a source conflict by keeping one primary document."""
        return await self._request_json(
            "POST", "/documents/source_conflicts/repair", json=request.model_dump(exclude_none=True)
        )

    async def clear_documents(self) -> dict[str, Any]:
        """Delete every document and all associated data."""
        return await self._request_json("DELETE", "/documents")

    async def clear_cache(self) -> dict[str, Any]:
        """Clear the LLM response cache."""
        return await self._request_json("POST", "/documents/clear_cache", json={})

    async def force_reset_recovery(self, confirm: bool) -> dict[str, Any]:
        """Force-clear the recovery_required fence raised after an interrupted job."""
        return await self._request_json(
            "POST", "/documents/recovery/force_reset", json={"confirm": confirm}
        )

    async def cancel_pipeline(self) -> dict[str, Any]:
        """Request cancellation of the running indexing pipeline."""
        return await self._request_json("POST", "/documents/cancel_pipeline")
