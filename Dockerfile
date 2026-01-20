# ---------- Stage 1: Python dependencies ----------
FROM python:3.9-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# ---------- Stage 2: FFmpeg runtime ----------
FROM jrottenberg/ffmpeg:6.1-ubuntu

# 🔴 VERY IMPORTANT: disable ffmpeg entrypoint
ENTRYPOINT []

WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:8000 app:app & python3 bot.py"]
