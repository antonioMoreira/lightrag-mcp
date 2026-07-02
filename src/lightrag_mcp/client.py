import httpx
from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Optional, Any, AsyncGenerator

# --- Pydantic Data Models ---

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

class ReferenceItem(BaseModel):
    reference_id: str
    file_path: str
    content: Optional[List[str]] = None

class QueryResponse(BaseModel):
    response: str
    references: Optional[List[ReferenceItem]] = None

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
            except httpx.RequestError as e:
                raise LightRAGClientError(f"HTTP connection error: {e}") from e
            except Exception as e:
                raise LightRAGClientError(f"Failed to process response: {e}") from e

    async def query_stream(self, request: QueryRequest) -> AsyncGenerator[str, None]:
        """Query streaming response chunks from LightRAG."""
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
                        if line:
                            # Strip SSE prefixes if present (e.g. "data: ")
                            if line.startswith("data: "):
                                yield line[6:]
                            else:
                                yield line
            except httpx.RequestError as e:
                raise LightRAGClientError(f"HTTP connection error: {e}") from e
            except Exception as e:
                raise LightRAGClientError(f"Failed to stream response: {e}") from e
