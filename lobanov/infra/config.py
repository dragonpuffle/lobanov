from collections.abc import Callable
from typing import ClassVar, override

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

from lobanov.infra.configs import (
    AppConfig,
    CORSConfig,
    CeleryConfig,
    HuggingFaceConfig,
    JWTConfig,
    NLPConfig,
    RateLimitConfig,
    STTConfig,
    StorageConfig,
    TextPreprocessingConfig,
)
from lobanov.infra.postgres import PostgresConfig


class GlobalConfig(BaseSettings):
    debug: bool = False

    app: AppConfig
    postgres: PostgresConfig
    jwt: JWTConfig
    cors: CORSConfig
    storage: StorageConfig
    stt: STTConfig
    nlp: NLPConfig
    text_preprocessing: TextPreprocessingConfig
    celery: CeleryConfig
    rate_limit: RateLimitConfig
    huggingface: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)

    @classmethod
    def load(cls) -> "GlobalConfig":
        return GlobalConfig()  # pyright: ignore[reportCallIssue]  # type: ignore[missing-argument]

    @classmethod
    def subconfigs(cls) -> list[Callable[["GlobalConfig"], object]]:
        """Generate getter functions for each unique type in the GlobalConfig model.
        This method generates a list of callables that can be used to extract sub-configurations.
        """
        getters: list[Callable[[GlobalConfig], object]] = []
        types_met: set[str] = set()

        for field_name, model_field in GlobalConfig.model_fields.items():
            target_type = model_field.annotation
            if target_type is None:
                continue

            if str(target_type) in types_met:
                continue
            types_met.add(str(target_type))

            def factory(field_name: str, output_type: type) -> Callable[["GlobalConfig"], object]:
                def getter(cfg: "GlobalConfig") -> object:
                    return getattr(cfg, field_name)  # pyright: ignore[reportAny]

                getter.__annotations__["return"] = output_type
                return staticmethod(getter)

            getters.append(factory(field_name, target_type))

        return getters

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="LOBANOV_",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        toml_file="config.toml",
    )

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # define custom priority
        return (
            init_settings,  # passed from code
            env_settings,  # loaded from active env variable
            dotenv_settings,  # loaded from .env file
            TomlConfigSettingsSource(settings_cls),  # loaded from toml config
            file_secret_settings,  # other file sources
        )
