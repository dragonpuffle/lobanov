# Lobanov — ассистент медицинской документации

Веб-приложение для полуавтоматического оформления медицинских документов: врач записывает или загружает аудио консультации, система транскрибирует речь, извлекает клинические факты и заполняет шаблон документа с возможностью проверки и экспорта.

**Стек:** FastAPI + PostgreSQL (backend), React + Vite (frontend).

## Возможности

- Сессии документирования и загрузка аудио
- Распознавание речи (Whisper / OpenRouter)
- Извлечение клинических фактов (Qwen / OpenRouter)
- Заполнение шаблонов, валидация и подтверждение полей
- Экспорт документов (PDF)
- JWT-аутентификация

## Структура проекта

```
.
├── lobanov/              # Backend (Clean/Hexagonal architecture)
│   ├── app/              # FastAPI, роутеры
│   ├── domain/           # Сущности
│   ├── usecases/         # Сценарии использования
│   ├── adapters/         # Реализации репозиториев и сервисов
│   └── infra/            # Конфиг, БД
├── frontend/             # React SPA (TanStack Router, shadcn/ui)
├── alembic/              # Миграции БД
├── experiments/          # Бенчмарки STT/NLP (не нужны для запуска)
├── docker-compose.yml
├── config.toml.example   # Пример конфигурации backend
├── pyproject.toml        # Python-зависимости (uv)
└── uv.lock
```

## Требования

| Компонент | Версия / примечание |
|-----------|---------------------|
| Python | 3.12 |
| [uv](https://docs.astral.sh/uv/) | менеджер зависимостей и venv |
| Node.js | 22+ (для frontend) |
| PostgreSQL | 17 (локально или через Docker) |
| **ffmpeg** | **обязателен** — конвертация аудио (mp3, m4a, ogg и др.) |
| Docker | опционально, для БД или полного стека |

**ffmpeg** должен быть в `PATH`. Без него загрузка не-mp3 файлов и часть STT-провайдеров не работают.

- Windows: `winget install Gyan.FFmpeg` или [ffmpeg.org](https://ffmpeg.org/download.html)
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`

Для локального Whisper на GPU нужен CUDA; для NLP — API-ключ OpenAI (или `use_mock = true` в конфиге).

## Конфигурация

```bash
cp .env.example .env
cp config.toml.example config.toml
```

**`.env`** — учётные данные PostgreSQL для Docker (`PG_APP_*`, `PG_ADM_*`).

**`config.toml`** — основные настройки backend. При запуске БД через Docker укажите:


Ключи STT/NLP, JWT secret и пути хранилища — в `config.toml`. Переменные окружения с префиксом `LOBANOV__` переопределяют значения из TOML.

## Запуск

### Вариант 1 — гибридный (рекомендуется для разработки)

БД в Docker, backend и frontend локально.

**1. PostgreSQL**

```bash
docker compose up lobanov_postgres -d
```

**2. Backend**

```bash
uv venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

uv sync
alembic upgrade head
uv run python -m lobanov.app
```

API: http://localhost:8000 · Swagger: http://localhost:8000/docs

**3. Frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

UI: http://localhost:5173 (Vite проксирует `/api` на backend).

### Вариант 2 — Docker

```bash
cp config.toml.example config.docker.toml
```

```bash
docker compose up --build
```

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:8080 |
| Backend API | http://localhost:8000 |
| PostgreSQL | localhost:5432 |


## Разработка

```bash
# Форматирование и линт (backend)
uv run ruff format
uv run ruff check

uv run mypy . --install-types --non-interactive --ignore-missing-imports --check-untyped-defs --disable-error-code var-annotated --disable-error-code import-untyped --disable-error-code type-abstract     
```

## Лицензия

См. файл LICENSE.
