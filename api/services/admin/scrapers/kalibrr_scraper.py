import datetime
import math
import random
import re
import time

from django.core.cache import cache
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from api.services.admin.scrapers.helper import (
    add_cookie_safely,
    close_driver,
    get_driver,
    is_task_cancelled,
    random_sleep,
    update_task_progress,
)


def authenticate_to_kalibrr(task_id: str) -> tuple:
    """Login ke Kalibrr dan return authenticated driver"""
    driver = get_driver()

    if driver is None:
        error_msg = "Failed to create Chrome driver"
        print(f"[KALIBRR_AUTH_ERROR] {error_msg}")
        return None, error_msg

    try:
        driver.get("https://www.kalibrr.com/login")
        driver.refresh()
        random_sleep(2, 3)

        if is_task_cancelled(task_id):
            return None, "Task cancelled"

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "login-email"))
        )

        email_field = driver.find_element(By.ID, "login-email")
        password_field = driver.find_element(By.ID, "login-password")

        email_field.clear()
        email_field.send_keys("scrapingkalibrr@gmail.com")

        password_field.clear()
        password_field.send_keys("scrapingkalibrr123")

        if is_task_cancelled(task_id):
            return None, "Task cancelled"

        # Submit login
        submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        random_sleep(2, 3)

        if is_task_cancelled(task_id):
            return None, "Task cancelled"

        driver.get(
            "https://jobseeker.kalibrr.com/job-board/i/it-and-software/1?sort=Freshness"
        )

        random_sleep(2, 3)

        if is_task_cancelled(task_id):
            return None, "Task cancelled"

        return driver, None

    except Exception as e:
        print(f"[KALIBRR_AUTH_ERROR] Authentication failed: {str(e)}")
        return None, error_msg


# ===== URL COLLECTION FUNCTIONS =====


def get_max_page_number(driver, task_id: str) -> int:
    """Mendapatkan jumlah maksimal halaman"""
    try:
        if is_task_cancelled(task_id):
            return 0

        # Cari elemen pagination
        page_span_element = driver.find_element(
            By.XPATH,
            "/html/body/kb-app-root/div/main/div/kb-job-board/div/div/div[1]/div[2]/kb-job-board-pagination/div/span",
        )

        if is_task_cancelled(task_id):
            return 0

        max_page = 1  # Default jika hanya ada 1 halaman

        if page_span_element:
            # Ambil teks dari elemen span
            pagination_text = page_span_element.text.strip()

            # Cari angka terakhir setelah "of" menggunakan regex
            # Pattern untuk menangkap angka setelah "of"
            match = re.search(r"of\s+(\d+)", pagination_text)

            if match:
                total_jobs = int(match.group(1))

                # Hitung max page (total jobs dibagi 15, lalu ceil)
                max_page = math.ceil(total_jobs / 15)
            else:
                # Fallback: coba cari semua angka dan ambil yang terbesar
                numbers = re.findall(r"\d+", pagination_text)
                if numbers:
                    total_jobs = int(numbers[-1])  # Ambil angka terakhir
                    max_page = math.ceil(total_jobs / 15)

        if is_task_cancelled(task_id):
            return 0

        return max_page
    except Exception as e:
        print(f"[KALIBRR_MAX_PAGE_ERROR] Failed to get max page number: {str(e)}")
        return 1


def collect_job_urls(
    driver,
    max_page: int,
    task_id: str,
) -> list[str]:
    """Mengumpulkan semua URL pekerjaan"""
    job_urls = []
    seen_urls = set()

    for page in range(1, max_page + 1):
        # for page in range(1, 2):
        try:
            if is_task_cancelled(task_id):
                break

            url = f"https://jobseeker.kalibrr.com/job-board/i/it-and-software/{page}?sort=Freshness"

            driver.get(url)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            random_sleep(2, 3)

            if is_task_cancelled(task_id):
                break

            job_link_elements = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        "//a[contains(@href, '/c/') and contains(@href, '/jobs/') and contains(@class, 'k-font-bold')]",
                    )
                )
            )

            if is_task_cancelled(task_id):
                break

            page_urls = set()  # Track URLs untuk halaman ini
            for job_link_element in job_link_elements:
                href = job_link_element.get_attribute("href")
                if href:
                    # Bersihkan URL dari query parameters
                    clean_url = href.split("?")[0]

                    # Cek apakah URL sudah ada di set
                    if clean_url not in seen_urls and clean_url not in page_urls:
                        job_urls.append(href)
                        seen_urls.add(clean_url)
                        page_urls.add(clean_url)

        except Exception as e:
            print(
                f"[KALIBRR_URL_COLLECTION_ERROR] Error collecting URLs from page {page}: {str(e)}"
            )
            continue

    if is_task_cancelled(task_id):
        return []

    return job_urls


def extract_company_logo(driver, task_id) -> str | None:
    """Ekstrak URL logo perusahaan"""
    if is_task_cancelled(task_id):
        return None

    try:
        img_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/kb-app-root/div/main/div/kb-job-full-page/div/div/kb-job-page/div/div/div[1]/div[1]/kb-company-logo/a/div/img",
                )
            )
        )

        return img_tag.get_attribute("src")

    except Exception:
        return "https://img.icons8.com/?size=720&id=53373&format=png&color=000000"


def extract_job_title(driver, task_id) -> str | None:
    """Ekstrak judul pekerjaan"""
    if is_task_cancelled(task_id):
        return None

    try:
        title_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/kb-app-root/div/main/div/kb-job-full-page/div/div/kb-job-page/div/div/div[1]/div[1]/h1",
                )
            )
        )
        return title_tag.get_attribute("textContent").strip()
    except Exception:
        return None


def extract_company_name(driver, task_id) -> str | None:
    """Ekstrak nama perusahaan"""
    if is_task_cancelled(task_id):
        return None

    try:
        company_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/kb-app-root/div/main/div/kb-job-full-page/div/div/kb-job-page/div/div/div[1]/div[1]/span/a/h2",
                )
            )
        )
        return company_tag.get_attribute("textContent").strip()
    except Exception:
        return None


def extract_location(driver, task_id) -> dict[str, str | None] | None:
    """Ekstrak informasi lokasi"""
    if is_task_cancelled(task_id):
        return None

    location = {"city": None}

    # Ekstrak kota
    try:
        location_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/kb-app-root/div/main/div/kb-job-full-page/div/div/kb-job-page/div/div/div[1]/div[1]/ul/li[1]/a",
                )
            )
        )

        # Cari elemen span dengan itemprop="addressLocality" untuk mendapatkan kota
        city_span = location_tag.find_element(
            By.XPATH, ".//span[@itemprop='addressLocality']"
        )

        location["city"] = city_span.text.strip()
    except Exception:
        pass

    if is_task_cancelled(task_id):
        return None

    return location


def extract_salary(driver, task_id) -> str | None:
    """Ekstrak informasi gaji"""
    if is_task_cancelled(task_id):
        return None

    try:
        # Cari elemen ul yang berisi informasi gaji
        ul_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/kb-app-root/div/main/div/kb-job-full-page/div/div/kb-job-page/div/div/div[1]/div[1]/ul",
                )
            )
        )

        # Cari elemen kb-salary-range di dalam ul
        salary_element = ul_element.find_element(
            By.XPATH, ".//a[contains(@href, '/job-board/sgt/')]"
        )

        # Ambil text dari elemen salary
        salary_text = salary_element.text.strip()

        # Validasi apakah ada angka dalam text gaji
        if salary_text and len(re.findall(r"[\d\.,]+", salary_text)) > 0:
            return salary_text
        else:
            return None

    except Exception:
        return None


def extract_employment_details(driver, task_id) -> dict[str, str | None] | None:
    """Ekstrak jenis pekerjaan dan cara kerja"""
    if is_task_cancelled(task_id):
        return None

    result = {"employment_type": None, "work_setup": "Kerja di kantor"}

    try:
        # Cari elemen ul yang berisi informasi employment details
        ul_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/kb-app-root/div/main/div/kb-job-full-page/div/div/kb-job-page/div/div/div[1]/div[1]/ul",
                )
            )
        )

        # Ekstrak employment type (Penuh waktu, Kontrak, dll.)
        try:
            employment_type_element = ul_element.find_element(
                By.XPATH, ".//a[contains(@href, '/job-board/t/')]"
            )
            result["employment_type"] = employment_type_element.text.strip()
        except Exception:
            pass

        # Ekstrak work setup (Hibrida, Jarak jauh, dll.)
        try:
            work_setup_element = ul_element.find_element(
                By.XPATH, ".//a[contains(@href, '/y/')]"
            )
            work_setup_spans = work_setup_element.find_elements(By.TAG_NAME, "span")
            work_setup_text = (
                work_setup_spans[1].get_attribute("textContent").strip()
                if len(work_setup_spans) > 1
                else ""
            )
            result["work_setup"] = work_setup_text
        except Exception:
            pass

        return result
    except Exception:
        return result


def extract_education(driver, task_id) -> str | None:
    """Ekstrak pendidikan minimum"""
    if is_task_cancelled(task_id):
        return None

    try:
        education_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[contains(@href, '/job-board/e/')]",
                )
            )
        )
        return education_tag.get_attribute("textContent").strip()
    except Exception as e:
        return None


def extract_description(driver, task_id) -> str | None:
    """Ekstrak deskripsi pekerjaan"""
    if is_task_cancelled(task_id):
        return None

    try:
        # Cari container utama yang berisi semua konten job description
        main_container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(@class, 'md:k-w-full md:k-pr-4 k-p-space')]",
                )
            )
        )

        description_parts = []

        # Ekstrak "Deskripsi Pekerjaan"
        try:
            job_desc_header = main_container.find_element(
                By.XPATH, ".//h2[contains(text(), 'Deskripsi Pekerjaan')]"
            )
            # Ambil div yang mengikuti header deskripsi pekerjaan
            job_desc_content = job_desc_header.find_element(
                By.XPATH, "./following-sibling::div[1]"
            )
            description_parts.append(f"<h2>Deskripsi Pekerjaan</h2>")
            description_parts.append(job_desc_content.get_attribute("innerHTML"))
        except Exception:
            pass

        # Ekstrak "Kualifikasi Minimum"
        try:
            qual_header = main_container.find_element(
                By.XPATH, ".//h2[contains(text(), 'Kualifikasi Minimum')]"
            )
            # Ambil div yang mengikuti header kualifikasi minimum
            qual_content = qual_header.find_element(
                By.XPATH, "./following-sibling::div[1]"
            )
            description_parts.append(f"<h2>Kualifikasi Minimum</h2>")
            description_parts.append(qual_content.get_attribute("innerHTML"))
        except Exception:
            pass

        # Gabungkan semua bagian
        if description_parts:
            full_description = "".join(description_parts)
            return full_description
        else:
            return None

    except Exception:
        return None


def extract_job_details(driver, job_url: str, task_id: str) -> dict[str, any] | None:
    """Ekstrak semua detail pekerjaan dari URL"""
    if is_task_cancelled(task_id):
        return None

    try:
        driver.get(job_url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep(1, 2)

        if is_task_cancelled(task_id):
            return None

        img_url = extract_company_logo(driver, task_id)

        if is_task_cancelled(task_id):
            return None

        title = extract_job_title(driver, task_id)

        if is_task_cancelled(task_id):
            return None

        company_name = extract_company_name(driver, task_id)

        if is_task_cancelled(task_id):
            return None

        location = extract_location(driver, task_id)

        if is_task_cancelled(task_id):
            return None

        salary = extract_salary(driver, task_id)

        if is_task_cancelled(task_id):
            return None

        employment_details = extract_employment_details(driver, task_id)

        if is_task_cancelled(task_id):
            return None

        education = extract_education(driver, task_id)

        if is_task_cancelled(task_id):
            return None

        description = extract_description(driver, task_id)

        if is_task_cancelled(task_id):
            return {}

        # Gabungkan hasil
        return {
            "job_url": job_url,
            "image_url": img_url,
            "job_title": title,
            "company_name": company_name,
            "subdistrict": None,
            "city": location["city"],
            "province": None,
            "salary": salary,
            "employment_type": employment_details["employment_type"],
            "work_setup": employment_details["work_setup"],
            "minimum_education": education,
            "minimum_experience": None,
            "required_skills": None,
            "job_description": description,
            "scraped_at": datetime.datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"[KALIBRR_JOB_DETAIL_ERROR] Error extracting job details: {str(e)}")
        return None


def scrape_kalibrr_jobs(
    task_id: str,
    update_state_func=None,
    scraped_jobs: int = 0,
) -> tuple[list[dict[str, any]], int] | tuple[list | None]:
    """Fungsi utama untuk scraping data Kalibrr"""
    progress_data = {"scraped_jobs": scraped_jobs}

    if is_task_cancelled(task_id):
        return []

    # 1. Login dan dapatkan cookies
    update_task_progress(
        task_id, "GETTING_KALIBRR_AUTH_DATA", progress_data, update_state_func
    )
    driver, auth_error = authenticate_to_kalibrr(task_id)

    if auth_error:
        return []

    if is_task_cancelled(task_id):
        return []

    try:
        if is_task_cancelled(task_id):
            return []

        update_task_progress(
            task_id, "GET_KALIBRR_MAX_PAGE", progress_data, update_state_func
        )

        # 3. Dapatkan jumlah halaman
        max_page = get_max_page_number(driver, task_id)

        update_task_progress(
            task_id, "COLLECT_KALIBRR_JOB_URLS", progress_data, update_state_func
        )

        if is_task_cancelled(task_id):
            return []

        # 4. Kumpulkan semua URL pekerjaan
        job_urls = collect_job_urls(driver, max_page, task_id)

        if is_task_cancelled(task_id):
            return []

        # 5. Scrape detail dari setiap URL
        update_task_progress(
            task_id,
            "SCRAPING_COLLECTED_KALIBRR_JOB_DETAIL",
            progress_data,
            update_state_func,
        )

        job_data = []
        for i, job_url in enumerate(job_urls[:10]):
            if is_task_cancelled(task_id):
                break

            try:
                job_detail = extract_job_details(driver, job_url, task_id)

                if job_detail is None:
                    print(
                        f"[KALIBRR_JOB_SKIP] Skipping job {i+1}/{len(job_urls[:10])}: No details extracted"
                    )
                    break

                job_data.append(job_detail)

                progress_data["scraped_jobs"] += 1
                update_task_progress(
                    task_id,
                    "SCRAPING_COLLECTED_KALIBRR_JOB_DETAIL",
                    progress_data,
                    update_state_func,
                )

            except Exception as e:
                print(
                    f"[KALIBRR_JOB_ERROR] Error processing job {i+1}/{len(job_urls[:10])} ({job_url}): {str(e)}"
                )
                continue

        if is_task_cancelled(task_id):
            return []

        return job_data

    except Exception as e:
        print(f"[KALIBRR_MAIN_ERROR] Fatal error in Kalibrr scraping: {str(e)}")
        return []
    finally:
        if driver:
            close_driver(driver)
