import os
import pytest
from lightrag_mcp.config import Settings

def test_settings_default():
    """Verify that default settings are loaded correctly."""
    settings = Settings()
    assert settings.lightrag_api_url == "http://localhost:9621"
    assert settings.request_timeout == 60.0

def test_settings_env_override(monkeypatch):
    """Verify that environment variables override defaults."""
    monkeypatch.setenv("LIGHTRAG_API_URL", "http://lightrag-sibling:9621")
    monkeypatch.setenv("REQUEST_TIMEOUT", "30.5")
    
    settings = Settings()
    assert settings.lightrag_api_url == "http://lightrag-sibling:9621"
    assert settings.request_timeout == 30.5
