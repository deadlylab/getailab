# GetAiLab — example lab Docker image
# Linux native · macOS/Windows via Docker Desktop
#
# Build:  docker compose build
# Run:    docker compose up -d
# Web:    http://localhost:5135

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    LAB_ID=example \
    PERSONAS_YAML=personas/example_squad.yaml \
    ORACLE_PORT=5124 \
    LAB_PORT=5135

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libreadline8 \
    libglib2.0-0 libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY lab/requirements.txt ./lab-requirements.txt
COPY scientists/requirements.txt ./scientists-requirements.txt

RUN pip install --upgrade pip && \
    pip install -r lab-requirements.txt && \
    pip install -r scientists-requirements.txt && \
    pip install python-dotenv && \
    (playwright install chromium --with-deps || playwright install chromium || true)

COPY . .

RUN mkdir -p logs data/labs/example dashboard/frontend data/screenshots && \
    chmod +x run_chimera.py desktop_launcher.py boot_example.sh docker.sh 2>/dev/null || true

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5135/health || exit 1

EXPOSE 5124 5125 5126 5135

CMD ["python", "lab/app_lab.py"]