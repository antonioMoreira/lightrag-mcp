from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import ValidationError
from typing import Literal, Optional

from lightrag_mcp.config import settings
from lightrag_mcp.client import LightRAGClient, QueryRequest

# Create FastMCP server instance
mcp = FastMCP("LightRAG Query MCP Server")

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
    only_need_context: Optional[bool] = None,
    only_need_prompt: Optional[bool] = None,
    response_type: Optional[str] = None,
    top_k: Optional[int] = None,
    chunk_top_k: Optional[int] = None,
    max_entity_tokens: Optional[int] = None,
    max_relation_tokens: Optional[int] = None,
    max_total_tokens: Optional[int] = None,
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
            output += "\n\n### References\n"
            for ref in response.references:
                output += f"- **[{ref.reference_id}]** `{ref.file_path}`\n"
                if include_chunk_content and ref.content:
                    for chunk in ref.content:
                        output += f"  > {chunk}\n"
        
        return output
    except Exception as e:
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
    only_need_context: Optional[bool] = None,
    only_need_prompt: Optional[bool] = None,
    response_type: Optional[str] = None,
    top_k: Optional[int] = None,
    chunk_top_k: Optional[int] = None,
    max_entity_tokens: Optional[int] = None,
    max_relation_tokens: Optional[int] = None,
    max_total_tokens: Optional[int] = None,
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
    except Exception as e:
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
    only_need_context: Optional[bool] = None,
    only_need_prompt: Optional[bool] = None,
    response_type: Optional[str] = None,
    top_k: Optional[int] = None,
    chunk_top_k: Optional[int] = None,
    max_entity_tokens: Optional[int] = None,
    max_relation_tokens: Optional[int] = None,
    max_total_tokens: Optional[int] = None,
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
    except Exception as e:
        return f"LightRAG Query Error: {e}"

def main():
    """Entry point for the MCP server."""
    mcp.run()
