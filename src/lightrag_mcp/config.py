from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    lightrag_api_url: str = Field(
        default="http://localhost:9621",
        description="The base URL of the running LightRAG REST server"
    )
    request_timeout: float = Field(
        default=60.0,
        description="The request timeout in seconds for communicating with the LightRAG REST server"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()
