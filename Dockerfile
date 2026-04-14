FROM python:3.12-slim

WORKDIR /app

# Install package and dependencies
COPY pyproject.toml .
COPY candle/ candle/
RUN pip install --no-cache-dir .

# Copy remaining files
COPY scripts/ scripts/
COPY alembic.ini .
COPY migrations/ migrations/

# Non-root user
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

CMD ["python", "scripts/run.py"]
