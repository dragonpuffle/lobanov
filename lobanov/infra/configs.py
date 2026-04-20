from pydantic import BaseModel, Field
from typing import List


class AppConfig(BaseModel):
    name: str = Field(description="Application name")
    environment: str = Field(description="Environment (development/production)")
    debug: bool = Field(description="Debug mode")
    log_level: str = Field(description="Logging level")


class PostgresConfig(BaseModel):
    host: str = Field(description="PostgreSQL host")
    port: int = Field(description="PostgreSQL port")
    username: str = Field(description="PostgreSQL username")
    password: str = Field(description="PostgreSQL password")
    database: str = Field(description="PostgreSQL database name")


class JWTConfig(BaseModel):
    secret_key: str = Field(description="JWT secret key")
    algorithm: str = Field(description="JWT algorithm")
    access_token_expire_minutes: int = Field(description="Access token expiration time in minutes")
    refresh_token_expire_days: int = Field(description="Refresh token expiration time in days")


class CORSConfig(BaseModel):
    origins: List[str] = Field(description="Allowed CORS origins")
    allow_credentials: bool = Field(description="Allow credentials")
    allow_methods: List[str] = Field(description="Allowed HTTP methods")
    allow_headers: List[str] = Field(description="Allowed HTTP headers")


class StorageConfig(BaseModel):
    audio_path: str = Field(description="Path to audio storage")
    max_audio_size: int = Field(description="Maximum audio file size in bytes")
    allowed_audio_formats: List[str] = Field(description="Allowed audio file formats")
    document_path: str = Field(description="Path to document storage")
    max_document_size: int = Field(description="Maximum document file size in bytes")


class STTConfig(BaseModel):
    model: str = Field(description="Speech-to-text model name")
    device: str = Field(description="Device to run model on (cpu/cuda)")
    language: str = Field(description="Language for speech recognition")


class NLPConfig(BaseModel):
    model: str = Field(description="NLP model name")
    api_key: str = Field(description="API key for NLP service")
    max_tokens: int = Field(description="Maximum tokens for NLP response")
    temperature: float = Field(description="Temperature for NLP generation")


class CeleryConfig(BaseModel):
    broker_url: str = Field(description="Celery broker URL")
    result_backend: str = Field(description="Celery result backend URL")


class RateLimitConfig(BaseModel):
    per_minute: int = Field(description="Requests per minute limit")
    per_hour: int = Field(description="Requests per hour limit")
