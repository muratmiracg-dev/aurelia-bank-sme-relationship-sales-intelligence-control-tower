FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AURELIA_SME_SALES_ROOT=/app

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY config ./config
COPY artifacts ./artifacts
USER appuser
EXPOSE 8000
CMD ["uvicorn", "aurelia_sme_sales.api:app", "--host", "0.0.0.0", "--port", "8000"]
