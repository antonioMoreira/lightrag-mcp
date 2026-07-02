import pytest
import httpx
from lightrag_mcp.client import (
    LightRAGClient,
    QueryRequest,
    QueryResponse,
    QueryDataResponse,
    LightRAGClientError,
)

@pytest.mark.asyncio
async def test_query_text_success(mocker):
    """Verify that query_text successfully maps and validates responses."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "This is a standard text response.",
        "references": [
            {
                "reference_id": "ref_001",
                "file_path": "doc1.txt",
                "content": ["Grounded context detail."]
            }
        ]
    }

    mock_client = mocker.AsyncMock()
    mock_client.post.return_value = mock_response

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621", timeout=30.0)
    request = QueryRequest(query="Explain LightRAG", mode="hybrid")
    
    res = await client.query_text(request)
    
    assert isinstance(res, QueryResponse)
    assert res.response == "This is a standard text response."
    assert len(res.references) == 1
    assert res.references[0].reference_id == "ref_001"
    assert res.references[0].file_path == "doc1.txt"
    assert res.references[0].content == ["Grounded context detail."]

    mock_client.post.assert_called_once_with(
        "http://localhost:9621/query",
        json={
            "query": "Explain LightRAG",
            "mode": "hybrid",
            "include_references": True,
            "include_chunk_content": False,
            "stream": False
        }
    )

@pytest.mark.asyncio
async def test_query_text_http_error(mocker):
    """Verify that HTTP non-200 responses raise LightRAGClientError."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_client = mocker.AsyncMock()
    mock_client.post.return_value = mock_response

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621")
    request = QueryRequest(query="Fail query")

    with pytest.raises(LightRAGClientError) as exc_info:
        await client.query_text(request)

    assert "server returned error status 500" in str(exc_info.value)
    assert "Internal Server Error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_query_text_request_error(mocker):
    """Verify that network-level request exceptions raise LightRAGClientError."""
    mock_client = mocker.AsyncMock()
    mock_client.post.side_effect = httpx.RequestError("Connection refused")

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621")
    request = QueryRequest(query="Unreachable host")

    with pytest.raises(LightRAGClientError) as exc_info:
        await client.query_text(request)

    assert "HTTP connection error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_query_text_parsing_error(mocker):
    """Verify that malformed JSON responses raise LightRAGClientError."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    # Invalid response format missing expected 'response' field
    mock_response.json.return_value = {"invalid_field": "no response here"}

    mock_client = mocker.AsyncMock()
    mock_client.post.return_value = mock_response

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621")
    request = QueryRequest(query="Malformed json")

    with pytest.raises(LightRAGClientError) as exc_info:
        await client.query_text(request)

    assert "Failed to process response" in str(exc_info.value)

@pytest.mark.asyncio
async def test_query_data_success(mocker):
    """Verify that query_data successfully retrieves structured knowledge data."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "message": "Retrieved 1 entities and 1 relationships",
        "data": {
            "entities": [{"name": "LightRAG", "type": "Technology"}],
            "relationships": []
        },
        "metadata": {"execution_time": 0.05}
    }

    mock_client = mocker.AsyncMock()
    mock_client.post.return_value = mock_response

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621")
    request = QueryRequest(query="Get structured LightRAG information", mode="mix")

    res = await client.query_data(request)

    assert isinstance(res, QueryDataResponse)
    assert res.status == "success"
    assert res.data["entities"][0]["name"] == "LightRAG"
    assert res.metadata["execution_time"] == 0.05

    mock_client.post.assert_called_once_with(
        "http://localhost:9621/query/data",
        json={
            "query": "Get structured LightRAG information",
            "mode": "mix",
            "include_references": True,
            "include_chunk_content": False,
        }
    )

@pytest.mark.asyncio
async def test_query_data_http_error(mocker):
    """Verify that non-200 responses in query_data raise LightRAGClientError."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    mock_client = mocker.AsyncMock()
    mock_client.post.return_value = mock_response

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621")
    request = QueryRequest(query="Fail structured query")

    with pytest.raises(LightRAGClientError) as exc_info:
        await client.query_data(request)

    assert "server returned error status 404" in str(exc_info.value)

@pytest.mark.asyncio
async def test_query_stream_success(mocker):
    """Verify that query_stream correctly parses and strips stream tokens."""
    mock_stream_response = mocker.MagicMock()
    mock_stream_response.status_code = 200

    # Mock dynamic generator for stream lines
    async def mock_aiter_lines():
        yield "data: Chunk"
        yield " "
        yield "one"
        yield "data:  and chunk"
        yield " two"

    mock_stream_response.aiter_lines = mock_aiter_lines

    mock_client = mocker.AsyncMock()
    mock_client.stream = mocker.MagicMock()
    
    mock_context_manager = mocker.AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_stream_response
    mock_client.stream.return_value = mock_context_manager

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621")
    request = QueryRequest(query="Stream query", mode="local")

    chunks = []
    async for chunk in client.query_stream(request):
        chunks.append(chunk)

    assert chunks == ["Chunk", " ", "one", " and chunk", " two"]

    mock_client.stream.assert_called_once_with(
        "POST",
        "http://localhost:9621/query/stream",
        json={
            "query": "Stream query",
            "mode": "local",
            "include_references": True,
            "include_chunk_content": False,
            "stream": True
        }
    )

@pytest.mark.asyncio
async def test_query_stream_http_error(mocker):
    """Verify that non-200 responses in query_stream raise LightRAGClientError."""
    mock_stream_response = mocker.AsyncMock()
    mock_stream_response.status_code = 400
    mock_stream_response.aread.return_value = b"Bad Request Parameter"

    mock_client = mocker.AsyncMock()
    mock_client.stream = mocker.MagicMock()
    
    mock_context_manager = mocker.AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_stream_response
    mock_client.stream.return_value = mock_context_manager

    mock_class = mocker.patch("httpx.AsyncClient")
    mock_class.return_value.__aenter__.return_value = mock_client

    client = LightRAGClient("http://localhost:9621")
    request = QueryRequest(query="Fail stream")

    with pytest.raises(LightRAGClientError) as exc_info:
        async for _ in client.query_stream(request):
            pass

    assert "server returned error status 400" in str(exc_info.value)
    assert "Bad Request Parameter" in str(exc_info.value)
