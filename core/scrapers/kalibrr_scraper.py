import random
import re
import time
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from core.scrapers.utils import close_driver, get_driver, is_task_cancelled

# ===== AUTHENTICATION FUNCTIONS =====


def authenticate_to_glints(task_id: str) -> tuple:
    """Login ke Glints dan mendapatkan cookies"""
    print("Mencoba login ke Glints")
    driver = get_driver()

    try:
        # Buka halaman login
        print("Membuka halaman login Glints")
        driver.get("https://glints.com/id/login")
        time.sleep(random.uniform(2, 4))

        # Klik tombol email login
        login_email_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@aria-label='Login with Email button']")
            )
        )
        login_email_button.click()

        # Isi email dan password
        email_field = driver.find_element(By.ID, "login-form-email")
        password_field = driver.find_element(By.ID, "login-form-password")

        email_field.send_keys("scrapingglints@gmail.com")
        password_field.send_keys("scrapingglints123")

        # Submit login
        submit_button = driver.find_element(
            By.XPATH, "//button[@data-cy='submit_btn_login']"
        )
        submit_button.click()

        # Verifikasi login
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (
                    By.XPATH,
                    "//h1[@class='ForYouTabHeadersc__Heading-sc-vgyvm0-0 euPYjq']",
                )
            )
        )

        # Ambil cookies
        cookies = driver.get_cookies()
        close_driver(driver)

        return cookies, None

    except Exception as e:
        error_msg = f"Error saat authenticate_to_glints: {str(e)}"
        print(error_msg)
        close_driver(driver)
        return None, error_msg


# ===== URL COLLECTION FUNCTIONS =====


def get_max_page_number(driver, task_id: str, update_progress_func=None) -> int:
    """Mendapatkan jumlah maksimal halaman"""
    try:
        pagination_buttons = driver.find_elements(
            By.XPATH, "//button[contains(@class, 'AnchorPaginationsc__Number')]"
        )

        max_page = 1  # Default jika hanya ada 1 halaman
        for button in pagination_buttons:
            try:
                page_num = int(button.text)
                if page_num > max_page:
                    max_page = page_num
            except ValueError:
                continue

        print(f"Halaman terakhir yang tersedia: {max_page}")

        if update_progress_func:
            progress_data = {"max_page": max_page}
            update_progress_func(task_id, "GETTING_MAX_PAGE_NUMBER", progress_data)

        return max_page
    except Exception as e:
        print(f"Error mendapatkan jumlah halaman: {e}")
        return 1


def collect_job_urls(
    driver, max_page: int, task_id: str, update_progress_func=None
) -> List[str]:
    """Mengumpulkan semua URL pekerjaan"""
    job_urls = []
    progress_data = {"max_page": max_page, "total_jobs": 0}

    for page in range(1, max_page + 1):
        try:
            if is_task_cancelled(task_id):
                print(f"Task dibatalkan saat scraping page ke-{page}.")
                break

            print(f"Scraping halaman {page}/{max_page}")
            url = f"https://glints.com/id/job-category/computer-technology"
            url = f"{url}?page={page}" if page > 1 else url

            driver.get(url)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(3, 5))

            job_title_tags = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//a[starts-with(@href, '/id/opportunities/jobs/')]")
                )
            )

            for job_title_tag in job_title_tags:
                job_urls.append(job_title_tag.get_attribute("href"))

            # Update progress
            progress_data["total_jobs"] = len(job_urls)
            if update_progress_func:
                update_progress_func(task_id, "COLLECTING_JOB_URLS", progress_data)

        except Exception as e:
            print(f"Error di halaman {page}: {e}")

    return job_urls


# ===== DETAIL EXTRACTION FUNCTIONS =====


def extract_company_logo(driver) -> Optional[str]:
    """Ekstrak URL logo perusahaan"""
    try:
        img_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[1]/img",
                )
            )
        )

        srcset = img_tag.get_attribute("srcset")
        urls = [item.strip().split(" ") for item in srcset.split(",")]
        url_dict = {int(size[:-1]): url for url, size in urls}
        return url_dict[max(url_dict.keys())]
    except Exception as e:
        print(f"Error ekstrak logo: {e}")
        return "https://img.icons8.com/?size=720&id=53373&format=png&color=000000"


def extract_job_title(driver) -> Optional[str]:
    """Ekstrak judul pekerjaan"""
    try:
        title_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[2]/div/div[1]/h1",
                )
            )
        )
        return title_tag.get_attribute("textContent").strip()
    except Exception as e:
        print(f"Error ekstrak judul: {e}")
        return None


def extract_company_name(driver) -> Optional[str]:
    """Ekstrak nama perusahaan"""
    try:
        company_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[2]/div/div[2]/div/a",
                )
            )
        )
        return company_tag.get_attribute("textContent").strip()
    except Exception as e:
        print(f"Error ekstrak nama perusahaan: {e}")
        return None


def extract_location(driver) -> Dict[str, Optional[str]]:
    """Ekstrak informasi lokasi"""
    location = {"subdistrict": None, "city": None, "province": None}

    # Ekstrak kecamatan
    try:
        subdistrict_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[1]/div/label[5]/a",
                )
            )
        )
        location["subdistrict"] = subdistrict_tag.get_attribute("textContent").strip()
    except Exception as e:
        print(f"Error ekstrak kecamatan: {e}")

    # Ekstrak kota
    try:
        city_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[1]/div/label[4]/a",
                )
            )
        )
        location["city"] = city_tag.get_attribute("textContent").strip()
    except Exception as e:
        print(f"Error ekstrak kota: {e}")

    # Ekstrak provinsi
    try:
        province_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[1]/div/label[3]/a",
                )
            )
        )
        location["province"] = province_tag.get_attribute("textContent").strip()
    except Exception as e:
        print(f"Error ekstrak provinsi: {e}")

    return location


def extract_salary(driver) -> Optional[str]:
    """Ekstrak informasi gaji"""
    try:
        salary_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[1]/div/span",
                )
            )
        )
        salary = salary_tag.get_attribute("textContent").strip()
        return salary if len(re.findall(r"[\d\.]+", salary)) > 0 else None
    except Exception:
        try:
            # Coba dengan XPath alternatif
            salary_tag = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[1]",
                    )
                )
            )
            salary = salary_tag.get_attribute("textContent").strip()
            return salary if len(re.findall(r"[\d\.]+", salary)) > 0 else None
        except Exception as e:
            print(f"Error ekstrak gaji: {e}")
            return None


def extract_employment_details(driver) -> Dict[str, Optional[str]]:
    """Ekstrak jenis pekerjaan dan cara kerja"""
    result = {"employment_type": None, "work_setup": None}

    try:
        details_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[3]",
                )
            )
        )

        details_text = details_tag.get_attribute("textContent").strip()
        if " · " in details_text:
            parts = details_text.split(" · ")
            result["employment_type"] = parts[0]
            result["work_setup"] = parts[1]
    except Exception as e:
        print(f"Error ekstrak detail pekerjaan: {e}")

    return result


def extract_education(driver) -> Optional[str]:
    """Ekstrak pendidikan minimum"""
    try:
        education_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[4]",
                )
            )
        )
        return education_tag.get_attribute("textContent").strip()
    except Exception as e:
        print(f"Error ekstrak pendidikan: {e}")
        return None


def extract_experience(driver) -> Optional[str]:
    """Ekstrak pengalaman minimum"""
    try:
        experience_tag = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[5]",
                )
            )
        )
        experience = experience_tag.get_attribute("textContent").strip()
        return experience if "pengalaman" in experience.lower() else None
    except Exception as e:
        print(f"Error ekstrak pengalaman: {e}")
        return None


def extract_skills(driver) -> List[str]:
    """Ekstrak skill yang dibutuhkan"""
    try:
        skills_container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(@class, 'Opportunitysc__SkillsContainer-sc-gb4ubh-10 jccjri')]",
                )
            )
        )

        time.sleep(random.uniform(2, 3))
        skill_tags = skills_container.find_elements(By.TAG_NAME, "label")
        return [tag.get_attribute("textContent").strip() for tag in skill_tags]
    except Exception as e:
        print(f"Error ekstrak skills: {e}")
        return []


def extract_description(driver) -> Optional[str]:
    """Ekstrak deskripsi pekerjaan"""
    try:
        description_container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(@class, 'DraftjsReadersc__ContentContainer-sc-zm0o3p-0 pVRwR')]",
                )
            )
        )
        return description_container.get_attribute("innerHTML")
    except Exception as e:
        print(f"Error ekstrak deskripsi: {e}")
        return None


def extract_job_details(driver, job_url: str) -> Dict[str, Any]:
    """Ekstrak semua detail pekerjaan dari URL"""
    print(f"Scraping detail for: {job_url}")
    driver.get(job_url)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(2, 3))

    # Ekstrak semua komponen
    img_url = extract_company_logo(driver)
    title = extract_job_title(driver)
    company_name = extract_company_name(driver)
    location = extract_location(driver)
    salary = extract_salary(driver)
    employment_details = extract_employment_details(driver)
    education = extract_education(driver)
    experience = extract_experience(driver)
    skills = extract_skills(driver)
    description = extract_description(driver)

    # Gabungkan hasil
    return {
        "job_url": job_url,
        "image_url": img_url,
        "job_title": title,
        "company_name": company_name,
        "subdistrict": location["subdistrict"],
        "city": location["city"],
        "province": location["province"],
        "salary": salary,
        "employment_type": employment_details["employment_type"],
        "work_setup": employment_details["work_setup"],
        "minimum_education": education,
        "minimum_experience": experience,
        "required_skills": skills,
        "job_description": description,
    }


# ===== PROGRESS MANAGEMENT FUNCTIONS =====


def update_task_progress(
    task_id: str, state: str, progress_data: Dict[str, Any], update_state_func=None
):
    """Update progres task di cache dan celery state"""
    cache.set(f"scraping_progress_{task_id}", progress_data, timeout=None)
    if update_state_func:
        update_state_func(state=state, meta=progress_data)


# ===== MAIN SCRAPING FUNCTION =====


def scrape_kalibrr_jobs(task_id: str, update_state_func=None) -> List[Dict[str, Any]]:
    """Fungsi utama untuk scraping data Glints"""
    start_time = time.time()
    print("Memulai scraping Glints...")
    progress_data = {}

    # 1. Login dan dapatkan cookies
    update_task_progress(task_id, "GETTING_AUTH_DATA", progress_data, update_state_func)
    cookies, auth_error = authenticate_to_glints(task_id)

    if auth_error or not cookies:
        print(f"Gagal login: {auth_error}")
        return []

    if is_task_cancelled(task_id):
        print("Task dibatalkan setelah login.")
        return []

    # 2. Inisialisasi driver baru dengan cookies
    driver = get_driver()
    try:
        # Set cookies
        driver.get("https://glints.com/id")
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Cookie tidak bisa ditambahkan: {e}")

        # Refresh dan navigasi
        driver.refresh()
        time.sleep(random.uniform(3, 5))
        driver.get("https://glints.com/id/job-category/computer-technology")

        # 3. Dapatkan jumlah halaman
        max_page = get_max_page_number(driver, task_id, update_task_progress)

        if is_task_cancelled(task_id):
            print("Task dibatalkan setelah mendapatkan jumlah halaman.")
            close_driver(driver)
            return []

        # 4. Kumpulkan semua URL pekerjaan
        job_urls = collect_job_urls(driver, max_page, task_id, update_task_progress)

        if is_task_cancelled(task_id):
            print("Task dibatalkan setelah mengumpulkan URL.")
            close_driver(driver)
            return []

        # 5. Scrape detail dari setiap URL
        progress_data = {
            "max_page": max_page,
            "total_jobs": len(job_urls),
            "scraped_jobs": 0,
        }
        update_task_progress(
            task_id, "SCRAPING_JOB_DETAIL", progress_data, update_state_func
        )

        job_data = []
        for i, job_url in enumerate(job_urls):
            if is_task_cancelled(task_id):
                print("Task dibatalkan saat scraping job detail.")
                break

            try:
                job_detail = extract_job_details(driver, job_url)
                job_data.append(job_detail)

                # Update progress
                progress_data["scraped_jobs"] = len(job_data)
                update_task_progress(
                    task_id, "SCRAPING_JOB_DETAIL", progress_data, update_state_func
                )

            except Exception as e:
                print(f"Error scraping detail {job_url}: {e}")

        end_time = time.time()
        print(
            f"Scraping selesai dalam {end_time - start_time:.2f} detik. Total: {len(job_data)} jobs"
        )
        return job_data

    except Exception as e:
        print(f"Error dalam proses scraping: {e}")
        return []
    finally:
        close_driver(driver)
