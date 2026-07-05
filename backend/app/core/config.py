from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "Boardly"
    app_version: str = "0.1.0"
    debug: bool = False

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database (sync — psycopg2)
    database_url: str = "postgresql+psycopg2://boardly:boardly@localhost:5432/boardly"

    # Search backend — "postgres" (default, no extra infra) or "opensearch"
    search_backend: str = "postgres"

    # OpenSearch (only used when search_backend=opensearch)
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str = "admin"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # File uploads (local disk)
    upload_folder: str = "uploads"
    max_upload_size_mb: int = 10

    # AWS S3 (planned)
    aws_region: str = "eu-west-1"
    s3_bucket: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
