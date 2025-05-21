FROM python:3.12-slim AS builder

# Install only build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev
WORKDIR /app
COPY requirements.txt .
# Install explicitly to system Python
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libatspi2.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 \
    libnspr4 libnss3 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 \
    libxrandr2 xdg-utils \
    default-jre \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy all packages from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Create directories
RUN mkdir -p /app/uploaded_files  

# Add non-root user
RUN addgroup --system celery && adduser --system --ingroup celery celery

# Ubah permission directory
RUN chown -R celery:celery /app
RUN chown -R celery:celery /app/uploaded_files 

# Copy application code
COPY ./talent_matching_server/ /app/talent_matching_server/
COPY ./core/ /app/core/
COPY ./manage.py /app/
COPY ./utils/ /app/utils/

# Install gunicorn explicitly to ensure it's accessible
RUN pip install --no-cache-dir gunicorn watchdog

# Set proper permissions
RUN chown -R celery:celery /app

# Add entrypoint script
COPY ./docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
USER celery

CMD ["/app/docker-entrypoint.sh"]

