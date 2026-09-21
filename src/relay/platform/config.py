"""Application configuration loaded from environment or Azure Key Vault."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class RelaySettings(BaseSettings):
    """Core settings for Project Relay services."""

    environment: str = "development"
    debug: bool = False

    # Databases
    database_url: str = "postgresql+asyncpg://relay_app:relay_password@localhost:5432/relay_db"
    redis_url: str = "redis://localhost:6379/0"

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "relay-agent-queue"

    # Azure Services
    azure_blob_connection_string: str | None = None
    azure_blob_audit_container: str = "audit-events"
    azure_key_vault_uri: str | None = None

    # Channel Secrets
    whatsapp_verify_token: str = "relay_dev_verify_token"
    whatsapp_app_secret: str = "relay_dev_secret"

    # LLM & Decision Providers
    default_llm_model: str = "gpt-4o-mini"
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str | None = "2024-02-15-preview"
    azure_openai_deployment_name: str | None = None
    jev_api_url: str | None = None
    jev_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = RelaySettings()
