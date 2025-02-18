# Gunakan image Python
FROM python:3.10

# Atur direktori kerja di dalam container
WORKDIR /app

# Copy file requirements
COPY requirements.txt .

# Install dependensi
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh project ke container
COPY . .

# Ekspos port Django (default: 8000)
EXPOSE 8000

# Perintah untuk menjalankan server Django
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "talent_matching_server.wsgi:application"]