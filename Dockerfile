# GET AI LAB / Project Chimera - Multi-Platform Docker (Web, CLI, Mobile backend)
# FULL SUPPORT: Linux (native), macOS (Docker Desktop), Windows (Docker Desktop + WSL2 recommended)
# Pure: serves the full living dashboard + all APIs + chat for mobile/PWA/CLI + desktop launcher
# Universal: same image powers Android/iOS via remote or local host. CLI inside container via profile.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# System deps for scientific + playwright (chromium) + sauron vision (cross-plat host)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libreadline8 \
    libglib2.0-0 libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY lab/requirements.txt ./lab-requirements.txt
COPY scientists/requirements.txt ./scientists-requirements.txt

RUN pip install --upgrade pip && \
    pip install -r lab-requirements.txt && \
    pip install -r scientists-requirements.txt && \
    pip install python-dotenv && \
    (playwright install chromium --with-deps || playwright install chromium || true)

# Copy entire project (preserves structure; .dockerignore keeps image lean)
COPY . .

# Runtime dirs — host volumes override data/logs/artifacts at run time
RUN mkdir -p logs lab/artifacts dashboard/frontend data/labs/chimera data/screenshots && \
    chmod +x run_chimera.py desktop_launcher.py boot_chimera.sh 2>/dev/null || true

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5035/health || exit 1

EXPOSE 5035 5024 5025 5026 5027 5028 5029 5032 5034 5038 5039 5040

# Default: run the lab (dashboard + APIs + chat for all platforms) as foreground.
# For full squad: docker-compose up or override CMD. On Win: use docker compose.
CMD ["python", "lab/app_lab.py"]

# Usage examples (portable — adjust volume syntax per host shell):
# docker build -t getailab .
# Linux/mac: docker run -p 5035:5035 --env-file .env -v $(pwd)/lab/artifacts:/app/lab/artifacts getailab
# Windows (PowerShell): docker run -p 5035:5035 --env-file .env -v ${PWD}/lab/artifacts:/app/lab/artifacts getailab
# Web + mobile PWA chat: http://localhost:5035 (installable on Android/iOS too)
# For CLI inside: docker compose run --rm cli   (or docker exec)
# Full boot: docker compose up -d ;  or inside container: python run_chimera.py --chat --support
# Desktop launcher inside container works for web portion. Full cross-platform parity guaranteed.