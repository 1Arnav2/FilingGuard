# Public dashboard image: the static export and the read-only results API on one origin.
# Holds no secrets, no data/ and no index; the live target route stays off (FILINGGUARD_LIVE_TARGET unset).

FROM node:24.11.0-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npx next build

FROM python:3.11.9-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements-serve.txt pyproject.toml ./
COPY src/ src/
RUN pip install -r requirements-serve.txt && pip install --no-deps . && rm -rf src build
COPY results/summary.json results/summary.json
COPY results/dashboard/ results/dashboard/
COPY --from=web /web/out web/out
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn filingguard.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
