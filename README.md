# Talent Matching Server (API)

Proyek ini adalah server API untuk aplikasi Talent Matching menggunakan **Django REST Framework**, dirancang untuk berkomunikasi dengan **Neo4j** dan **Apache Jena Fuseki**.

## Persyaratan

Pastikan Anda sudah menginstal software berikut sebelum memulai:

- **Python**: Versi 3.10 atau lebih baru
- **Pip**: Untuk mengelola dependensi Python
- **Neo4j**: Untuk penyimpanan data berbasis graf
- **Apache Jena Fuseki**: Untuk query data berbasis ontologi

## Instalasi

Ikuti langkah-langkah di bawah untuk menjalankan proyek ini di lingkungan pengembangan lokal Anda.

### 1. Clone Repository

Clone repository ke komputer lokal Anda:

```bash
git clone <repository-url>
cd talent-matching-server
```

### 2. Buat dan Aktifkan Virtual Environment

Disarankan untuk menggunakan virtual environment agar paket Python terisolasi.

```bash
python -m venv env
source venv/bin/activate  # Untuk Linux/Mac
venv\Scripts\activate     # Untuk Windows
```

### 3. Instal Dependensi

Instal semua dependensi yang terdaftar di requirements.txt:

```bash
pip install -r requirements.txt
```

### 4. Buat Database di Neo4j

Pastikan sudah ada database di Neo4j dan aktifkan database tersebut.

### 5. Konfigurasi Koneksi Neo4j

Ubah isi di bagian file talent_matching/settings.py sesuai database yang telah dibuat:

```bash
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_database_password"
```

### 6. Jalankan Server

Migrate dan jalankan server:

```bash
python manage.py migrate
python manage.py runserver
```
