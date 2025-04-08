# Talent Matching Server (API) 🚀

![Docker](https://img.shields.io/badge/Docker-Containerization-blue)
![Django REST Framework](https://img.shields.io/badge/DRF-Django%20REST%20Framework-red)
![Neo4j](https://img.shields.io/badge/Neo4j-Graph%20Database-green)
![Redis](https://img.shields.io/badge/Cache-Redis-red)
![Celery](https://img.shields.io/badge/Celery-V5-orange)

Proyek ini adalah server API untuk aplikasi Talent Matching menggunakan **Django REST Framework**, dirancang untuk berkomunikasi dengan **Neo4j**.

## ✨ Fitur Utama

- 🔍 **Pencocokan Kandidat** – Menganalisis data graf dari **Neo4j** untuk menemukan kandidat terbaik berdasarkan keterampilan dan pengalaman.
- 🛠️ **Scraping Lowongan Pekerjaan** – Mengambil data pekerjaan dari berbagai sumber dengan **Selenium**.
- 🚀 **RESTful API** – Backend berbasis **Django REST Framework** untuk akses data yang cepat dan aman.
- ⚡ **Caching & Queue Processing** – **Redis** digunakan untuk caching hasil pencarian dan antrean tugas scraping dengan **Celery**.
- 📦 **Docker Support** – Dapat dijalankan dengan mudah menggunakan Docker Compose.

## 📂 Struktur Proyek

```
talent-matching-server/
│── core/
    │── serializers/
        │── ....
    │── views/
        │── ....
    │── admin.py
    │── apps.py
    │── models.py
    │── tasks.py
    │── tests.py
    │── urls.py
│── talent_matching_server/
    │── asgi.py
    │── celery.py
    │── settings.py
    │── urls.py
    │── wsgi.py
│── utils/
    │── custom_jwt_authentication.py
    │── exception_handler.py
│── .env.example
│── .gitignore
│── docker-compose-dev.yml
│── docker-compose-prod.yml
│── Dockerfile
│── manage.py
│── README.md
│── requirements.txt
```

## 🛠️ Persyaratan

Pastikan Anda sudah menginstal software berikut sebelum memulai:

- **Docker**: Untuk menjalankan aplikasi di atas container docker
- **Python**: Versi 3.12 atau lebih baru
- **Pip**: Untuk mengelola dependensi Python
- **Neo4j Desktop**: Untuk monitoring data graf

## 📦 Instalasi

Ikuti langkah-langkah di bawah untuk menjalankan proyek ini di lingkungan pengembangan lokal Anda.

### 1️⃣ Clone Repository

Clone repository ke komputer lokal Anda:

```bash
git clone https://github.com/RizkiGunawan23/talent-matching-server.git
cd talent-matching-server
```

### 2️⃣ Buat dan Aktifkan Virtual Environment

Disarankan untuk menggunakan virtual environment agar paket Python terisolasi.

```bash
python -m venv venv
source venv/bin/activate        # Untuk Linux/Mac
source venv/Scripts/activate    # Untuk Windows
```

### 3️⃣ Buat File .env dan Ubah Konfigurasi

Copy dan paste file .env.example dan rename menjadi .env.
Ubah bagian username dan password Neo4j mengikuti variabel NEO4J_AUTH di file docker-compose-dev.yml atau docker-compose-prod.yml. Contoh:

```bash
NEO4J_BOLT_URL=bolt://neo4j:12345678@neo4j:7687
```

## 🚀 Menjalankan dengan Docker

| Mode                    | Perintah                                               |
| ----------------------- | ------------------------------------------------------ |
| Development             | `docker compose -f docker-compose-dev.yml watch`       |
| Production (First Time) | `docker compose -f docker-compose-prod.yml up --build` |
| Production (Next Time)  | `docker compose -f docker-compose-prod.yml up`         |

### 🛑 Perintah Tambahan:

| Perintah                 | Deskripsi                        |
| ------------------------ | -------------------------------- |
| `docker-compose down`    | Hentikan & hapus container       |
| `docker-compose down -v` | Hapus container & volume (Neo4j) |

## 🛠️ Menambahkan Package Python

Jika ingin menambahkan package Python baru ke proyek, ikuti langkah berikut:

### 1️⃣ Install Package Baru

Jalankan perintah berikut untuk menginstal package yang dibutuhkan:

```bash
pip install <nama-package>
```

### 2️⃣ Perbarui requirements.txt

Setelah menginstal package, pastikan daftar dependensi proyek diperbarui dengan menjalankan:

```bash
pip freeze > requirements.txt
```
