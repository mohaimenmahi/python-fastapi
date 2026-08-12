# Base Image
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies Stage
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development Stage
FROM dependencies AS development

COPY . .

RUN adduser --disabled-password --gecos '' appuser && \
  chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]

# Production Stage
FROM dependencies AS production

COPY . .

RUN adduser --disabled-password --gecos '' appuser && \
  chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
