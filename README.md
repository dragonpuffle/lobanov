# Medical Documentation Assistant Backend

A backend system for semi-automatic generation of medical documents using audio input and an NLP pipeline.

## Features

- Audio upload and transcription using OpenAI Whisper
- Clinical fact extraction from transcripts
- Template-based document generation
- Draft review and verification with traceability
- RESTful API built with FastAPI
- Clean/Hexagonal architecture

## Project Structure

```
lobanov/
├── app/              # Application layer (FastAPI app, routers)
├── domain/           # Domain layer (entities, value objects, domain services)
├── infra/            # Infrastructure layer (database, config, adapters)
├── protocols/        # Protocols
├── usecases/         # Use cases (application services)
├── utils/            # Utilities (logging, helpers)
├── adapters/         # Adapters - protocol implementations
└── pyproject.toml    # Project dependencies
```

## Setup

### Prerequisites

- Python 3.12
- PostgreSQL database
- uv (package manager)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd lobanov
```

2. Install dependencies using uv:
```bash
uv venv
.venv/bin/activate
uv sync
```

3. Copy the example environment file:
```bash
cp .env.example .env
```

4. Configure your environment variables in `.env`:
- Set up your database connection string
- Configure JWT secret key
- Set up API keys for external services (OpenAI, etc.)

5. Run the application:
```bash
uv run python -m lobanov.app
```

The API will be available at `http://localhost:8000`

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`

## Development

### Code Formatting

```bash
uv run ruff format
uv run ruff check
```

### Type Checking

```bash
uv run mypy . --install-types --non-interactive --ignore-missing-imports --check-untyped-defs --disable-error-code var-annotated --disable-error-code import-untyped --disable-error-code type-abstract     
```

## License

See LICENSE file for details.
