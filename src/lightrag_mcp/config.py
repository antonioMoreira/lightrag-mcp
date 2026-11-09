from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    lightrag_api_url: str = Field(
        default="http://localhost:9621",
        description="The base URL of the running LightRAG REST server"
    )
    request_timeout: float = Field(
        default=60.0,
        description="The request timeout in seconds for communicating with the LightRAG REST server"
    )
    enable_admin_tools: bool = Field(
        default=False,
        validation_alias="LIGHTRAG_ENABLE_ADMIN_TOOLS",
        description="Expose bulk-destructive document tools (clear all, clear cache, force reset, cancel, repair)"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()
