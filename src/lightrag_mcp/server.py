import json
from collections.abc import Awaitable
from typing import Any, Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from lightrag_mcp.client import (
    DeleteDocRequest,
    DocStatus,
    DocumentsRequest,
    InsertTextRequest,
    InsertTextsRequest,
    LightRAGClient,
    LightRAGClientError,
    QueryRequest,
    SourceConflictRepairRequest,
    TextChunkingConfig,
)
from lightrag_mcp.config import settings

# Create FastMCP server instance
mcp = FastMCP("LightRAG MCP Server")

# Initialize the LightRAG client with configured parameters
client = LightRAGClient(
    base_url=settings.lightrag_api_url,
    timeout=settings.request_timeout
)

@mcp.tool(
    title="Query Rust/gRPC/QUIC Text Knowledge Base",
    description=(
        "Query the specialized local knowledge base for detailed text explanations, code patterns, and "
        "architectural guidelines regarding the Rust programming language, gRPC/Protobuf protocols, and QUIC/UDP networking. "
        "CRITICAL: ONLY invoke this tool for Rust, gRPC, or QUIC queries. Do NOT use for general programming languages "
        "(like Python, JS, C++) or general topics, as it will return irrelevant noise and pollute your reasoning."
    ),
    tags={"rust", "grpc", "quic", "rag"},
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
)
async def query_text(
    query: str,
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = "mix",
    only_need_context: bool | None = None,
    only_need_prompt: bool | None = None,
    response_type: str | None = None,
    top_k: int | None = None,
    chunk_top_k: int | None = None,
    max_entity_tokens: int | None = None,
    max_relation_tokens: int | None = None,
    max_total_tokens: int | None = None,
    include_references: bool = True,
    include_chunk_content: bool = False,
) -> str:
    """Query the specialized local knowledge base for detailed text explanations, code patterns, and 
    architectural guidelines regarding the Rust programming language, gRPC/Protobuf protocols, and QUIC/UDP networking.

    CRITICAL RULES:
    1. ONLY invoke this tool when the query explicitly relates to Rust, gRPC, Protobuf, or QUIC.
    2. Do NOT use this tool for other programming languages (like Python, JS, C++) or general topics, 
       as it will return irrelevant context and pollute your reasoning.
    3. This is the primary, default tool to use for standard text questions in these domains.

    Args:
        query: The prompt or question to ask the RAG system (minimum 3 characters).
        mode: The query retrieval mode. Defaults to 'mix'.
        only_need_context: If true, returns only the retrieved context chunks.
        only_need_prompt: If true, returns only the compiled prompt sent to LLM.
        response_type: Defines specific response format (e.g. 'Bullet Points').
        top_k: Number of entities/relations/nodes to retrieve.
        chunk_top_k: Number of raw text chunks to retrieve.
        max_entity_tokens: Token budget for entities.
        max_relation_tokens: Token budget for relations.
        max_total_tokens: Overall maximum tokens budget.
        include_references: Include reference items in the final output. Defaults to True.
        include_chunk_content: Include actual chunk contents inside the reference list. Defaults to False.
    """
    try:
        request = QueryRequest(
            query=query,
            mode=mode,
            only_need_context=only_need_context,
            only_need_prompt=only_need_prompt,
            response_type=response_type,
            top_k=top_k,
            chunk_top_k=chunk_top_k,
            max_entity_tokens=max_entity_tokens,
            max_relation_tokens=max_relation_tokens,
            max_total_tokens=max_total_tokens,
            include_references=include_references,
            include_chunk_content=include_chunk_content,
        )
    except ValidationError as e:
        return f"Input Validation Error: {e}"

    try:
        response = await client.query_text(request)
        output = response.response
        
        # Format references beautifully
        if include_references and response.references:
            # Prevent duplicate top-level '### References' headers if the LLM response already generated one
            if "### References" in output or "## References" in output:
                output += "\n\n### Source File Mappings\n"
            else:
                output += "\n\n### References\n"
            
            for ref in response.references:
                output += f"- **[{ref.reference_id}]** `{ref.file_path}`\n"
                if include_chunk_content and ref.content:
                    for chunk in ref.content:
                        output += f"  > {chunk}\n"
        
        return output
    except LightRAGClientError as e:
        return f"LightRAG Query Error: {e}"

@mcp.tool(
    title="Query Rust/gRPC/QUIC Graph Data",
    description=(
        "Retrieve raw, structured knowledge graph data (JSON entities, relations, raw text chunks, and graph nodes) "
        "from the specialized Rust, gRPC, and QUIC local knowledge base. Use this ONLY when you need to inspect raw "
        "JSON connections, node definitions, or compile custom graph metrics. For standard text questions, use query_text."
    ),
    tags={"rust", "grpc", "quic", "graph", "raw-data"},
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
)
async def query_data(
    query: str,
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = "mix",
    only_need_context: bool | None = None,
    only_need_prompt: bool | None = None,
    response_type: str | None = None,
    top_k: int | None = None,
    chunk_top_k: int | None = None,
    max_entity_tokens: int | None = None,
    max_relation_tokens: int | None = None,
    max_total_tokens: int | None = None,
) -> str:
    """Query structured knowledge graph data (entities, relations, chunks, etc.) from the specialized Rust, gRPC, and QUIC knowledge base.

    CRITICAL RULES:
    1. ONLY invoke this tool when the query explicitly relates to Rust, gRPC, Protobuf, or QUIC.
    2. Do NOT use this tool for standard natural language questions (use query_text instead).
    3. Use this tool ONLY when you need to inspect raw JSON graph entities, node definitions, 
       entity-relation lists, or compile custom graph connectivity metrics.

    Args:
        query: The prompt or question to ask (minimum 3 characters).
        mode: The query retrieval mode. Defaults to 'mix'.
        only_need_context: If true, returns only the retrieved context chunks.
        only_need_prompt: If true, returns only the compiled prompt sent to LLM.
        response_type: Defines specific response format (e.g. 'Bullet Points').
        top_k: Number of entities/relations/nodes to retrieve.
        chunk_top_k: Number of raw text chunks to retrieve.
        max_entity_tokens: Token budget for entities.
        max_relation_tokens: Token budget for relations.
        max_total_tokens: Overall maximum tokens budget.
    """
    try:
        request = QueryRequest(
            query=query,
            mode=mode,
            only_need_context=only_need_context,
            only_need_prompt=only_need_prompt,
            response_type=response_type,
            top_k=top_k,
            chunk_top_k=chunk_top_k,
            max_entity_tokens=max_entity_tokens,
            max_relation_tokens=max_relation_tokens,
            max_total_tokens=max_total_tokens,
        )
    except ValidationError as e:
        return f"Input Validation Error: {e}"

    try:
        response = await client.query_data(request)
        return response.model_dump_json(indent=2)
    except LightRAGClientError as e:
        return f"LightRAG Query Error: {e}"

@mcp.tool(
    title="Query Rust/gRPC/QUIC Stream Fallback",
    description=(
        "Query the specialized local Rust, gRPC, and QUIC knowledge base using a streaming aggregation fallback. "
        "Returns the fully aggregated text response. Prefer query_text as the primary tool; use this only if you specifically "
        "want to consume a server-sent events (SSE) stream aggregation under the hood."
    ),
    tags={"rust", "grpc", "quic", "rag", "stream"},
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
)
async def query_stream(
    query: str,
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = "mix",
    only_need_context: bool | None = None,
    only_need_prompt: bool | None = None,
    response_type: str | None = None,
    top_k: int | None = None,
    chunk_top_k: int | None = None,
    max_entity_tokens: int | None = None,
    max_relation_tokens: int | None = None,
    max_total_tokens: int | None = None,
) -> str:
    """Query the specialized local Rust, gRPC, and QUIC knowledge base using a streaming aggregation fallback.

    CRITICAL RULES:
    1. ONLY invoke this tool when the query explicitly relates to Rust, gRPC, Protobuf, or QUIC.
    2. Prefer using query_text as the primary tool. Use this tool only if you specifically want to stream 
       or consume token-by-token server-sent events (SSE) under the hood for highly long, continuous, or high-throughput queries.

    Args:
        query: The prompt or question to ask (minimum 3 characters).
        mode: The query retrieval mode. Defaults to 'mix'.
        only_need_context: If true, returns only the retrieved context chunks.
        only_need_prompt: If true, returns only the compiled prompt sent to LLM.
        response_type: Defines specific response format.
        top_k: Number of entities/relations/nodes to retrieve.
        chunk_top_k: Number of raw text chunks to retrieve.
        max_entity_tokens: Token budget for entities.
        max_relation_tokens: Token budget for relations.
        max_total_tokens: Overall maximum tokens budget.
    """
    try:
        request = QueryRequest(
            query=query,
            mode=mode,
            only_need_context=only_need_context,
            only_need_prompt=only_need_prompt,
            response_type=response_type,
            top_k=top_k,
            chunk_top_k=chunk_top_k,
            max_entity_tokens=max_entity_tokens,
            max_relation_tokens=max_relation_tokens,
            max_total_tokens=max_total_tokens,
        )
    except ValidationError as e:
        return f"Input Validation Error: {e}"

    try:
        chunks = []
        async for chunk in client.query_stream(request):
            chunks.append(chunk)
        return "".join(chunks)
    except LightRAGClientError as e:
        return f"LightRAG Query Error: {e}"

# --- Document Tools ---

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)

async def _document_call(call: Awaitable[dict[str, Any]]) -> str:
    """Await a document client call and render its JSON result or error."""
    try:
        return json.dumps(await call, indent=2, ensure_ascii=False)
    except LightRAGClientError as e:
        return f"LightRAG Document Error: {e}"

@mcp.tool(tags={"documents"}, annotations=WRITE)
async def upload_document(file_path: str) -> str:
    """Upload a local file (PDF, DOCX, TXT, MD, ...) to LightRAG and queue it for indexing.

    The path is resolved on the machine running this MCP server. When the server runs in Docker,
    the file's directory must be mounted into the container. Indexing runs in the background:
    use the returned track_id with get_track_status to see whether it finished or failed.
    A file whose name already exists in LightRAG is rejected with HTTP 409.

    Args:
        file_path: Absolute path of the file to upload.
    """
    return await _document_call(client.upload_document(file_path))

@mcp.tool(tags={"documents"}, annotations=WRITE)
async def insert_text(
    text: str,
    file_source: str | None = None,
    chunking_strategy: Literal["fixed_token", "recursive_character", "semantic_vector", "paragraph_semantic", "custom"] | None = None,
    chunking_params: dict[str, Any] | None = None,
) -> str:
    """Insert raw text into LightRAG and queue it for indexing.

    Args:
        text: The text content to insert.
        file_source: Source name recorded for citations (e.g. 'notes/meeting.md').
        chunking_strategy: Chunking strategy. Defaults to the server's fixed_token strategy.
        chunking_params: Strategy-specific chunking parameters.
    """
    try:
        request = InsertTextRequest(
            text=text,
            file_source=file_source,
            chunking=_chunking(chunking_strategy, chunking_params),
        )
    except ValidationError as e:
        return f"Input Validation Error: {e}"
    return await _document_call(client.insert_text(request))

@mcp.tool(tags={"documents"}, annotations=WRITE)
async def insert_texts(
    texts: list[str],
    file_sources: list[str] | None = None,
    chunking_strategy: Literal["fixed_token", "recursive_character", "semantic_vector", "paragraph_semantic", "custom"] | None = None,
    chunking_params: dict[str, Any] | None = None,
) -> str:
    """Insert several texts into LightRAG in one batch and queue them for indexing.

    Args:
        texts: The text contents to insert.
        file_sources: Source names recorded for citations, one per text.
        chunking_strategy: Chunking strategy. Defaults to the server's fixed_token strategy.
        chunking_params: Strategy-specific chunking parameters.
    """
    try:
        request = InsertTextsRequest(
            texts=texts,
            file_sources=file_sources,
            chunking=_chunking(chunking_strategy, chunking_params),
        )
    except ValidationError as e:
        return f"Input Validation Error: {e}"
    return await _document_call(client.insert_texts(request))

def _chunking(strategy: str | None, params: dict[str, Any] | None) -> TextChunkingConfig | None:
    """Build a chunking config only when the caller asked for one."""
    if strategy is None and not params:
        return None
    return TextChunkingConfig.model_validate({"strategy": strategy or "fixed_token", "params": params or {}})

@mcp.tool(tags={"documents"}, annotations=READ_ONLY)
async def list_documents(
    status_filters: list[DocStatus] | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_field: Literal["created_at", "updated_at", "id", "file_path"] = "updated_at",
    sort_direction: Literal["asc", "desc"] = "desc",
) -> str:
    """List documents in LightRAG with their IDs, file paths and processing status.

    Args:
        status_filters: Only include these statuses (pending, parsing, analyzing, processing, processed, failed).
        page: Page number (1-based).
        page_size: Documents per page (10-200).
        sort_field: Field to sort by.
        sort_direction: Sort direction.
    """
    try:
        request = DocumentsRequest(
            status_filters=status_filters,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
    except ValidationError as e:
        return f"Input Validation Error: {e}"
    return await _document_call(client.list_documents(request))

@mcp.tool(tags={"documents"}, annotations=READ_ONLY)
async def get_track_status(track_id: str) -> str:
    """Get the processing status and any error of documents created by an upload or insert.

    Args:
        track_id: The track_id returned by upload_document, insert_text or insert_texts.
    """
    return await _document_call(client.get_track_status(track_id))

@mcp.tool(tags={"documents"}, annotations=READ_ONLY)
async def get_status_counts() -> str:
    """Get the number of documents in each processing status."""
    return await _document_call(client.get_status_counts())

@mcp.tool(tags={"documents"}, annotations=READ_ONLY)
async def get_pipeline_status() -> str:
    """Get the current state of the LightRAG indexing pipeline (busy, current job, progress, messages)."""
    return await _document_call(client.get_pipeline_status())

@mcp.tool(tags={"documents"}, annotations=READ_ONLY)
async def get_supported_file_types() -> str:
    """Get the file extensions LightRAG accepts for upload."""
    return await _document_call(client.get_supported_file_types())

@mcp.tool(tags={"documents"}, annotations=WRITE)
async def scan_documents() -> str:
    """Scan the LightRAG server's input directory for new files and queue them for indexing.

    Use get_scan_status with the returned track_id to follow the scan.
    """
    return await _document_call(client.scan_documents())

@mcp.tool(tags={"documents"}, annotations=READ_ONLY)
async def get_scan_status(track_id: str) -> str:
    """Get the status of a scan started with scan_documents.

    Args:
        track_id: The track_id returned by scan_documents.
    """
    return await _document_call(client.get_scan_status(track_id))

@mcp.tool(tags={"documents"}, annotations=WRITE)
async def reprocess_failed_documents() -> str:
    """Requeue failed and pending documents for processing (e.g. after fixing an LLM or embedding outage)."""
    return await _document_call(client.reprocess_failed())

@mcp.tool(tags={"documents"}, annotations=DESTRUCTIVE)
async def delete_documents(
    doc_ids: list[str],
    delete_file: bool = False,
    delete_llm_cache: bool = False,
) -> str:
    """Permanently delete documents and all their entities, relations and chunks by ID.

    Only call this when the user explicitly asked to delete these documents.

    Args:
        doc_ids: IDs of the documents to delete (from list_documents or get_track_status).
        delete_file: Also delete the source file in LightRAG's input directory.
        delete_llm_cache: Also delete cached LLM extraction results for these documents.
    """
    try:
        request = DeleteDocRequest(doc_ids=doc_ids, delete_file=delete_file, delete_llm_cache=delete_llm_cache)
    except ValidationError as e:
        return f"Input Validation Error: {e}"
    return await _document_call(client.delete_documents(request))

@mcp.tool(tags={"documents"}, annotations=READ_ONLY)
async def list_source_conflicts(limit: int = 50, cursor: str | None = None) -> str:
    """List documents that share the same canonical source and need a primary chosen.

    Args:
        limit: Maximum conflicts to return (1-200).
        cursor: next_cursor from a previous page.
    """
    if not 1 <= limit <= 200:
        return "Input Validation Error: limit must be between 1 and 200"
    return await _document_call(client.list_source_conflicts(limit=limit, cursor=cursor))

# --- Admin Tools (disabled unless LIGHTRAG_ENABLE_ADMIN_TOOLS=true) ---

@mcp.tool(tags={"documents", "admin"}, annotations=DESTRUCTIVE)
async def clear_documents() -> str:
    """Permanently delete EVERY document and all knowledge graph data in LightRAG.

    Only call this when the user explicitly asked to wipe the entire knowledge base.
    """
    return await _document_call(client.clear_documents())

@mcp.tool(tags={"documents", "admin"}, annotations=DESTRUCTIVE)
async def clear_cache() -> str:
    """Clear LightRAG's entire LLM response cache."""
    return await _document_call(client.clear_cache())

@mcp.tool(tags={"documents", "admin"}, annotations=DESTRUCTIVE)
async def force_reset_recovery(confirm: bool = False) -> str:
    """Force-clear the recovery_required fence raised when a job died mid-write.

    The workspace may be partially committed. Only reset after the user verified or repaired it.

    Args:
        confirm: Must be true to perform the reset.
    """
    return await _document_call(client.force_reset_recovery(confirm))

@mcp.tool(tags={"documents", "admin"}, annotations=DESTRUCTIVE)
async def cancel_pipeline() -> str:
    """Request cancellation of the running indexing pipeline."""
    return await _document_call(client.cancel_pipeline())

@mcp.tool(tags={"documents", "admin"}, annotations=DESTRUCTIVE)
async def repair_source_conflict(
    canonical_source_key: str,
    primary_doc_id: str,
    dry_run: bool = True,
    expected_candidate_count: int | None = None,
    expected_candidate_fingerprint: str | None = None,
) -> str:
    """Resolve a source conflict by keeping one primary document.

    Run with dry_run=true first, then commit with dry_run=false, echoing the candidate_count and
    fingerprint from the dry run as expected_candidate_count and expected_candidate_fingerprint.

    Args:
        canonical_source_key: Canonical source key from list_source_conflicts.
        primary_doc_id: Document ID to keep as the single primary.
        dry_run: Report only instead of committing. Defaults to True.
        expected_candidate_count: candidate_count from the dry run (required to commit).
        expected_candidate_fingerprint: fingerprint from the dry run (required to commit).
    """
    try:
        request = SourceConflictRepairRequest(
            canonical_source_key=canonical_source_key,
            primary_doc_id=primary_doc_id,
            dry_run=dry_run,
            expected_candidate_count=expected_candidate_count,
            expected_candidate_fingerprint=expected_candidate_fingerprint,
        )
    except ValidationError as e:
        return f"Input Validation Error: {e}"
    return await _document_call(client.repair_source_conflict(request))

if not settings.enable_admin_tools:
    mcp.disable(tags={"admin"})

def main():
    """Entry point for the MCP server."""
    mcp.run()
