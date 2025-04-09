# Gunakan image Python
FROM python:3.12

# Atur direktori kerja di dalam container
WORKDIR /app

RUN apt-get update && apt-get install -y wget curl unzip gnupg \
    && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install \
    && rm google-chrome-stable_current_amd64.deb

# Copy file requirements
COPY requirements.txt .

# Install dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh project ke container
COPY . .

# Ekspos port Django (default: 8000)
EXPOSE 8000

# Tambah user untuk celery
RUN addgroup --system celery && adduser --system --ingroup celery celery

# Buat folder log dan kasih akses ke user celery
RUN mkdir -p /var/log/scraper && chown -R celery:celery /var/log/scraper

# Atur agar proses dijalankan oleh user celery
USER celery
# Perintah untuk menjalankan server Django
CMD ["gunicorn", "--reload", "--workers=1", "--threads=1", "--bind", "0.0.0.0:8000", "talent_matching_server.wsgi:application"]

