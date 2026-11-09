import json
import httpx
from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Optional, Any, AsyncGenerator

# --- Pydantic Data Models ---

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=65536, description="The query text")
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = Field(
        default="mix", description="Query mode"
    )
    only_need_context: Optional[bool] = Field(None, description="If True, only returns context")
    only_need_prompt: Optional[bool] = Field(None, description="If True, only returns prompt")
    response_type: Optional[str] = Field(
        None, min_length=1, max_length=256, description="Defines the response format (e.g. 'Bullet Points')"
    )
    top_k: Optional[int] = Field(None, ge=1, le=1000, description="Number of top items to retrieve")
    chunk_top_k: Optional[int] = Field(None, ge=1, le=1000, description="Number of text chunks to retrieve")
    max_entity_tokens: Optional[int] = Field(None, ge=1, le=1000000, description="Max entity tokens")
    max_relation_tokens: Optional[int] = Field(None, ge=1, le=1000000, description="Max relation tokens")
    max_total_tokens: Optional[int] = Field(None, ge=1, le=1000000, description="Max total tokens budget")
    hl_keywords: Optional[List[str]] = Field(None, max_length=64, description="High-level keywords")
    ll_keywords: Optional[List[str]] = Field(None, max_length=64, description="Low-level keywords")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Chat history")
    user_prompt: Optional[str] = Field(None, max_length=65536, description="User customized prompt instructions")
    disable_user_prompt_prefix: Optional[bool] = Field(
        None,
        description="If True, the server-side global prompt prefix is not prepended to user_prompt"
    )
    enable_rerank: Optional[bool] = Field(None, description="Enable reranking")
    include_references: Optional[bool] = Field(True, description="Include reference list")
    include_chunk_content: Optional[bool] = Field(False, description="Include actual chunk content")
    include_progress: Optional[bool] = Field(
        None,
        description="If True, emits retrieval pipeline progress events before response chunks in /query/stream"
    )
    stream: Optional[bool] = Field(None, description="Stream output flag")

class ReferenceItem(BaseModel):
    reference_id: str
    file_path: str
    content: Optional[List[str]] = None

class QueryResponse(BaseModel):
    response: str
    references: Optional[List[ReferenceItem]] = None
    response_time: Optional[float] = None
    llm_generated: bool = True

class QueryDataResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]

# --- Custom Exception ---

class LightRAGClientError(Exception):
    """Exception raised for errors in the LightRAG client."""
    pass

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

    async def query_stream(self, request: QueryRequest) -> AsyncGenerator[str, None]:
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
                        cleaned = line[6:] if line.startswith("data: ") else line
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
