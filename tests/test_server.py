import pytest
from pydantic import ValidationError
from lightrag_mcp.server import query_text, query_data, query_stream, client
from lightrag_mcp.client import (
    QueryResponse,
    QueryDataResponse,
    ReferenceItem,
    LightRAGClientError,
)

@pytest.mark.asyncio
async def test_server_query_text_success(mocker):
    """Verify that query_text tool executes successfully and formats references."""
    mock_response = QueryResponse(
        response="This is the answer from LightRAG.",
        references=[
            ReferenceItem(
                reference_id="ref_001",
                file_path="manual.md",
                content=["Instruction set detail."]
            )
        ]
    )
    mock_query_text = mocker.patch.object(client, "query_text", return_value=mock_response)

    res = await query_text(
        query="How to run",
        mode="global",
        include_references=True,
        include_chunk_content=True
    )

    assert "This is the answer from LightRAG." in res
    assert "### References" in res
    assert "[ref_001]" in res
    assert "`manual.md`" in res
    assert "> Instruction set detail." in res

    # Verify correct parameters were passed to the client method
    mock_query_text.assert_called_once()
    called_request = mock_query_text.call_args[0][0]
    assert called_request.query == "How to run"
    assert called_request.mode == "global"
    assert called_request.include_references is True
    assert called_request.include_chunk_content is True

@pytest.mark.asyncio
async def test_server_query_text_validation_error():
    """Verify that query_text tool returns validation error for short queries."""
    res = await query_text(query="ab")  # Short query < 3 characters
    assert "Input Validation Error" in res

@pytest.mark.asyncio
async def test_server_query_text_client_error(mocker):
    """Verify that query_text tool handles client-level exceptions gracefully."""
    mocker.patch.object(
        client,
        "query_text",
        side_effect=LightRAGClientError("API is down")
    )

    res = await query_text(query="Valid query but client fails")
    assert "LightRAG Query Error: API is down" in res

@pytest.mark.asyncio
async def test_server_query_data_success(mocker):
    """Verify that query_data tool returns structured json."""
    mock_response = QueryDataResponse(
        status="success",
        message="Ok",
        data={"nodes": [], "edges": []},
        metadata={}
    )
    mock_query_data = mocker.patch.object(client, "query_data", return_value=mock_response)

    res = await query_data(query="Get data structure")
    assert '"status": "success"' in res
    assert '"message": "Ok"' in res
    assert '"nodes": []' in res

    mock_query_data.assert_called_once()

@pytest.mark.asyncio
async def test_server_query_stream_success(mocker):
    """Verify that query_stream tool aggregates chunked responses."""
    async def mock_stream_generator(*args, **kwargs):
        yield "Streaming"
        yield " "
        yield "RAG"
        yield " "
        yield "Response"

    mock_query_stream = mocker.patch.object(
        client,
        "query_stream",
        side_effect=mock_stream_generator
    )

    res = await query_stream(query="Run stream")
    assert res == "Streaming RAG Response"
    mock_query_stream.assert_called_once()
