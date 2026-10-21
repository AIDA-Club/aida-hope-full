# syntax=docker/dockerfile:1
# AIDA × Hope web redesign: one container serving the React site and its FastAPI backend.
#
#   docker build -t aida-hope .
#   docker run --rm -p 10000:10000 -e AIDA_API_KEY=... aida-hope      # key optional
#
# Render sets PORT; locally it defaults to 10000. Secrets are never baked in: the live
# Ask AIDA settings come from AIDA_PROVIDER / AIDA_API_KEY / AIDA_MODEL (+ optional
# AIDA_BASE_URL, AIDA_DAILY_CALL_CAP) at run time. Without them Ask AIDA answers offline.

# ---------------------------------------------------------------- 1. frontend build
FROM node:22.12.0-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------- 2. Python dependencies
FROM python:3.12.10-slim-bookworm AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements-web.txt ./
RUN /opt/venv/bin/pip install -r requirements-web.txt

# ---------------------------------------------------------------- 3. runtime
FROM python:3.12.10-slim-bookworm
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000
RUN useradd --create-home --uid 10001 aida
WORKDIR /app

COPY --from=deps /opt/venv /opt/venv

# Python code the API imports (the Streamlit pages themselves are not needed).
COPY api/ ./api/
COPY booth.py aida_chat.py challenge_logic.py tweak_logic.py slide_image.py ./
# Translations and the Ask AIDA knowledge base (system prompt + offline answers).
COPY i18n/ ./i18n/
COPY kb/ ./kb/
# Tweak the Tumor model, its feature metadata/presets, and the microscope images.
COPY models/wdbc_model.pkl models/wdbc_features.json ./models/
COPY data/slide/ ./data/slide/
# Can you beat the AI?: the 30 booth cases and their original / heatmap / overlay images,
# plus patient folder 6. (Print images are only used for the printed cards.)
COPY data/booth_set.json ./data/
COPY data/images/ ./data/images/
COPY data/heatmaps/ ./data/heatmaps/
COPY data/overlays/ ./data/overlays/
COPY data/folders/ ./data/folders/
# About: results and the two real example images (folder 6, not a booth card).
COPY data/reports/metrics.json data/reports/confusion_matrix.png ./data/reports/
COPY data/reports/gradcam_all/originals/malignant_id_153.png ./data/reports/gradcam_all/originals/
COPY data/reports/gradcam_all/heatmaps/malignant_id_153.png ./data/reports/gradcam_all/heatmaps/
# The built website (fonts are bundled into dist/assets by @fontsource).
COPY --from=web /web/dist ./frontend/dist

# Everything above is read-only for the app user; the API never writes files.
USER aida
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"10000\")}/api/health', timeout=4)"

# One worker on purpose: visitor sessions (game rounds, chat) are kept in process memory.
# --proxy-headers: Render terminates HTTPS in front of the container.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port \"${PORT:-10000}\" --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
