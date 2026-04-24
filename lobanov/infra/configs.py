from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = Field(description="Application name")
    environment: str = Field(description="Environment (development/production)")
    debug: bool = Field(description="Debug mode")
    log_level: str = Field(description="Logging level")


class JWTConfig(BaseModel):
    secret_key: str = Field(description="JWT secret key")
    algorithm: str = Field(description="JWT algorithm")
    access_token_expire_minutes: int = Field(description="Access token expiration time in minutes")
    refresh_token_expire_days: int = Field(description="Refresh token expiration time in days")


class CORSConfig(BaseModel):
    origins: list[str] = Field(description="Allowed CORS origins")
    allow_credentials: bool = Field(description="Allow credentials")
    allow_methods: list[str] = Field(description="Allowed HTTP methods")
    allow_headers: list[str] = Field(description="Allowed HTTP headers")


class StorageConfig(BaseModel):
    audio_path: str = Field(description="Path to audio storage")
    max_audio_size: int = Field(description="Maximum audio file size in bytes")
    allowed_audio_formats: list[str] = Field(description="Allowed audio file formats")
    document_path: str = Field(description="Path to document storage")
    max_document_size: int = Field(description="Maximum document file size in bytes")


class STTConfig(BaseModel):
    provider: str = Field(description="Speech-to-text provider (whisper/gigaam/openrouter)")
    model: str = Field(description="Speech-to-text model name (OpenRouter model id when provider=openrouter)")
    api_key: str = Field(
        default="",
        description="API key for remote STT (OpenRouter); empty for local whisper/gigaam",
    )
    device: str = Field(description="Device to run model on (cpu/cuda)")
    language: str = Field(description="Default language for speech recognition (e.g. ru)")
    revision: str = Field(description="Model revision for Hugging Face (GigaAM); use empty string for Whisper")
    compute_type: str = Field(description="Model compute type (e.g. int8, float16, float32)")
    beam_size: int = Field(description="Beam size for decoder")
    vad_filter: bool = Field(description="Enable VAD filtering")
    word_timestamps: bool = Field(description="Return word timestamps from STT model")
    temperature: float = Field(description="Decoding temperature for STT")
    no_speech_threshold: float | None = Field(
        default=None,
        description="No speech threshold for decoding; omit from decoder when unset",
    )
    condition_on_previous_text: bool = Field(description="Condition segments on previous text")
    initial_prompt: str = Field(description="Initial prompt for domain adaptation; empty string to disable")


class NLPConfig(BaseModel):
    use_mock: bool = Field(description="Use mock extractor instead of LLM")
    model: str = Field(description="NLP model name")
    api_key: str = Field(description="API key for NLP service")
    max_tokens: int = Field(description="Maximum tokens for NLP response")
    temperature: float = Field(description="Temperature for NLP generation")
    use_structured_output: bool = Field(description="Use JSON schema structured output mode")
    use_response_healing: bool = Field(description="Use response-healing plugin for malformed JSON recovery")


class TextPreprocessingConfig(BaseModel):
    lowercase: bool = Field(description="Lowercase text during cleaning")
    remove_special_chars: bool = Field(description="Strip special characters during cleaning")


class CeleryConfig(BaseModel):
    broker_url: str = Field(description="Celery broker URL")
    result_backend: str = Field(description="Celery result backend URL")


class RateLimitConfig(BaseModel):
    per_minute: int = Field(description="Requests per minute limit")
    per_hour: int = Field(description="Requests per hour limit")


class HuggingFaceConfig(BaseModel):
    token: str = Field(
        default="",
        description="Hugging Face Hub access token (read is enough for public models); empty = anonymous",
    )
