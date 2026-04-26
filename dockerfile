FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS python3

RUN apt update && apt upgrade -y && apt install -y ffmpeg

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --compile-bytecode

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Читаем config.toml из рабочей каталога (в compose: volume → config.docker.toml)
CMD ["python", "-m", "lobanov.app"]
