FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev --no-install-project 

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", \
     "bookstore_api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
