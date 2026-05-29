FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt .
RUN python -m pip install --upgrade pip \
    && pip install -r requirements-web.txt

COPY backend ./backend
COPY assets ./assets
COPY web ./web
COPY web_app.py .

RUN mkdir -p uploads separated/web

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
