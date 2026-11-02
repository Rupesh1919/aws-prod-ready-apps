"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Claims API")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="local")
    log_level: str = Field(default="INFO")

    # Database
    database_host: str = Field(default="localhost")
    database_port: int = Field(default=5432)
    database_name: str = Field(default="claims_db")
    database_user: str = Field(default="claims_user")
    database_password: str = Field(default="")
    database_ssl_mode: str = Field(default="prefer")
    database_pool_size: int = Field(default=5)
    database_max_overflow: int = Field(default=10)
    database_pool_timeout: int = Field(default=30)
    database_pool_recycle: int = Field(default=3600)

    # Server
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)
    server_workers: int = Field(default=1)
    server_reload: bool = Field(default=False)

    # Authentication
    auth_enabled: bool = Field(default=True)
    jwt_issuer: str = Field(default="")
    jwt_audience: str = Field(default="")
    jwt_algorithms: str = Field(default="RS256")
    jwks_url: str = Field(default="")
    jwks_cache_ttl: int = Field(default=3600)

    # OpenAPI
    openapi_enabled: bool = Field(default=False)
    openapi_url: str | None = Field(default="/api/openapi.json")
    docs_url: str | None = Field(default="/api/docs")

    # Health checks
    health_db_timeout: int = Field(default=5)

    # Pagination
    default_page_size: int = Field(default=20)
    max_page_size: int = Field(default=100)

    # Request limits
    max_description_length: int = Field(default=2000)
    correlation_id_header: str = Field(default="X-Correlation-ID")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return upper_v

    @field_validator("jwt_algorithms")
    @classmethod
    def validate_algorithms(cls, v: str) -> str:
        """Validate JWT algorithms."""
        allowed = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
        algs = {alg.strip() for alg in v.split(",")}
        invalid = algs - allowed
        if invalid:
            raise ValueError(f"Invalid JWT algorithms: {invalid}. Allowed: {allowed}")
        return v

    @property
    def jwt_algorithms_list(self) -> list[str]:
        """Get JWT algorithms as a list."""
        return [alg.strip() for alg in self.jwt_algorithms.split(",")]

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() in ("prod", "production")

    @property
    def is_local(self) -> bool:
        """Check if running locally."""
        return self.environment.lower() in ("local", "dev", "development")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
