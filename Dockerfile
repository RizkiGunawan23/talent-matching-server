# Gunakan image Python
FROM python:3.12

# Atur direktori kerja di dalam container
WORKDIR /app

# Install dependencies sistem yang dibutuhkan oleh Chrome dan ChromeDriver
# RUN apt-get update && apt-get install -y \
#     wget curl unzip libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 \
#     && rm -rf /var/lib/apt/lists/*

# # Download dan install Google Chrome
# RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
#     && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
#     && apt-get update && apt-get install -y google-chrome-stable \
#     && rm -rf /var/lib/apt/lists/*

# # Download dan install ChromeDriver
# RUN CHROME_DRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
#     wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip && \
#     unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
#     rm /tmp/chromedriver.zip && \
#     chmod +x /usr/local/bin/chromedriver
RUN apt-get update && apt-get install -y wget curl unzip \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*


# Copy file requirements
COPY requirements.txt .

# Install dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh project ke container
COPY . .

# Ekspos port Django (default: 8000)
EXPOSE 8000

RUN addgroup --system celery && adduser --system --ingroup celery celery
USER celery
# Perintah untuk menjalankan server Django
# CMD ["gunicorn", "--reload", "--bind", "0.0.0.0:8000", "talent_matching_server.wsgi:application"]
# CMD ["gunicorn", "--workers=$(nproc)", "--threads=2", "--bind", "0.0.0.0:8000", "talent_matching_server.wsgi:application"]
CMD ["gunicorn", "--workers=4", "--threads=2", "--bind", "0.0.0.0:8000", "talent_matching_server.wsgi:application"]

