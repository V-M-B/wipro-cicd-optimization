# Baseline image for the analytics service.
# NOTE: the layer ordering is intentionally naive (copy everything, then install),
# so any source change invalidates the dependency layer. This is the "legacy"
# baseline that later caching optimizations are measured against.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/analytics

COPY . .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 analytics
USER analytics

EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
