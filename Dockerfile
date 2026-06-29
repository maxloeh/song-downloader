# ─── Stage 1: build the React frontend ───────────────────────────────────────
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: python runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# System deps: ffmpeg (conversion + cover embed), deno (yt-dlp JS edge cases),
# curl/ca-certs for installs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (used by some yt-dlp YouTube extractions).
ENV DENO_INSTALL=/usr/local
RUN curl -fsSL https://deno.land/install.sh | sh \
    && deno --version

# Non-root user; /downloads owned by it.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Python deps. Install the backend package + engines.
COPY backend/pyproject.toml ./backend/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "fastapi>=0.111" "uvicorn[standard]>=0.30" "pydantic>=2.7" \
        "pydantic-settings>=2.3" "python-multipart>=0.0.9" \
        "yt-dlp>=2024.0.0" "spotdl>=4.2.0" "mutagen>=1.47"

# App code + built frontend.
COPY backend/ ./backend/
COPY --from=frontend /build/dist ./backend/static
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/downloads \
    PORT=8080

RUN mkdir -p /downloads && chown -R appuser:appuser /downloads /app
USER appuser
WORKDIR /app/backend

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
