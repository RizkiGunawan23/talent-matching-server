# Base stage - Install semua dependencies sekali
FROM python:3.12-slim AS base

# Environment variables untuk optimasi pip
ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev wget curl ca-certificates fonts-liberation \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
    libcups2 libdbus-1-3 libdrm2 libgbm1 libnspr4 libnss3 \
    libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 \
    libxrandr2 xdg-utils default-jre && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    (dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install) && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip wheel setuptools

# Install Python packages
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Django stage - untuk web server
FROM base AS django

WORKDIR /app

# Create directories
RUN mkdir -p /app/uploaded_files

# Add non-root user
RUN addgroup --system django && adduser --system --ingroup django django

# Copy application code
COPY ./talent_matching_server/ /app/talent_matching_server/
COPY ./core/ /app/core/
COPY ./manage.py /app/
COPY ./utils/ /app/utils/

# Set ownership
RUN chown -R django:django /app

EXPOSE 8000
USER django

CMD ["gunicorn", "--workers=1", "--threads=1", "--bind", "0.0.0.0:8000", "talent_matching_server.wsgi:application"]

# Celery stage - untuk worker
FROM base AS celery

WORKDIR /app

# Create directories
RUN mkdir -p /app/uploaded_files

# Add non-root user
RUN addgroup --system celery && adduser --system --ingroup celery celery

# Copy application code
COPY ./talent_matching_server/ /app/talent_matching_server/
COPY ./core/ /app/core/
COPY ./manage.py /app/
COPY ./utils/ /app/utils/

# Set ownership - perbaikan di sini
RUN chown -R celery:celery /app

USER celery

CMD ["celery", "-A", "talent_matching_server", "worker", "--loglevel=info"]