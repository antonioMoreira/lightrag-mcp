from fastmcp import FastMCP
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

@mcp.tool()
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
    """Query standard text response from LightRAG.

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

@mcp.tool()
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
    """Query structured knowledge graph data (entities, relations, chunks, etc.) from LightRAG.

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

@mcp.tool()
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
    """Query streaming response chunks from LightRAG and return the aggregated response.

    This connects to the streaming endpoint, consumes all token chunks in real-time,
    and returns the fully aggregated text response.

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
