# Cloud Run container for Bhagya.
# Single-stage build using uv (the same tool we use in dev).
#
# Why slim, not alpine: pyswisseph + sqlite3 link against glibc, not musl.
# We install gcc + python3-dev because pyswisseph's current release doesn't
# ship a manylinux wheel for Python 3.12 (yet) — it builds from source.
# Final image is ~350MB; multi-stage could shrink it but the simpler
# single-stage is easier to reason about.

FROM python:3.12-slim

# Build toolchain — needed for pyswisseph's source build on linux/3.12.
# build-essential pulls gcc + g++ + make (pyswisseph bundles sqlite3
# C++ sources, so g++ alone wasn't enough).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally (single binary; fastest Python toolchain available).
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy lockfile + manifest first so layer cache survives source edits.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Ship .pyc alongside the .py in the venv. uv doesn't compile bytecode by
# default, so without this every cold container re-compiles ~2000 modules
# from source on first import — pure cold-start latency on Cloud Run, where
# container layers are streamed lazily.
ENV UV_COMPILE_BYTECODE=1

# Install runtime deps + the package, frozen to uv.lock; skip dev deps.
RUN uv sync --frozen --no-dev

# Same treatment for our own package (uv's flag only covers what it installs).
RUN /app/.venv/bin/python -m compileall -q /app/src

# Cloud Run injects $PORT (defaults to 8080); listen on it.
ENV PORT=8080

# Cloud Run filesystems are read-only EXCEPT /tmp. Put the SQLite cache there
# so put/get works at runtime. Cache survives within an instance's lifetime
# (typically minutes to hours), gets wiped on cold start — fine for us since
# chart data lives in user cookies and cache misses just re-trigger LLM calls.
ENV BHAGYA_CACHE_DB=/tmp/bhagya.db

EXPOSE 8080

# uvicorn invoked straight from the venv. `uv run` would re-resolve the
# environment on every container start before exec'ing the same binary;
# calling it directly skips that. sh -c stays because ${PORT} needs expanding.
#
# --proxy-headers + --forwarded-allow-ips="*" tells uvicorn to trust
# X-Forwarded-Host / X-Forwarded-Proto set by the reverse proxy in
# front of Cloud Run (Firebase Hosting / Google Frontend / Fastly).
# Without these flags, FastAPI's automatic trailing-slash redirect
# generates Location: http://bhagya-<hash>.a.run.app/... — the
# internal Cloud Run URL — instead of https://shubhagya.com/...,
# which Google Search Console flags as "Redirect error" and stops
# indexing those pages. `*` is safe here: the app is only reachable
# via the trusted proxy, no direct client can spoof headers.
CMD ["sh", "-c", "/app/.venv/bin/uvicorn astro_ai.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips=*"]
