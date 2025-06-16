import datetime
import random
import re
import time

from django.core.cache import cache
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from api.services.scrapers.helper import (
    close_driver,
    get_driver,
    is_task_cancelled,
    update_task_progress,
)


def authenticate_to_glints(task_id: str) -> tuple:
    """Login ke Glints dan mendapatkan cookies"""
    driver = get_driver()

    try:
        # Buka halaman login
        driver.get("https://glints.com/id/login")
        time.sleep(random.uniform(2, 4))

        if is_task_cancelled(task_id):
            return None, None

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

        if is_task_cancelled(task_id):
            return None, None

        # Submit login
        submit_button = driver.find_element(
            By.XPATH, "//button[@data-cy='submit_btn_login']"
        )
        submit_button.click()

        if is_task_cancelled(task_id):
            return None, None

        # Verifikasi login
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (
                    By.XPATH,
                    "//h1[@class='ForYouTabHeadersc__Heading-sc-vgyvm0-0 euPYjq']",
                )
            )
        )

        if is_task_cancelled(task_id):
            return None, None

        # Ambil cookies
        cookies = driver.get_cookies()
        close_driver(driver)

        return cookies, None

    except Exception as e:
        error_msg = f"Error saat authenticate_to_glints: {str(e)}"
        close_driver(driver)
        return None, error_msg


# ===== URL COLLECTION FUNCTIONS =====


def get_max_page_number(driver, task_id: str, update_progress_func=None) -> int:
    """Mendapatkan jumlah maksimal halaman"""
    try:
        if update_progress_func:
            update_progress_func(task_id, "GETTING_GLINTS_MAX_PAGE_NUMBER", {})

        if is_task_cancelled(task_id):
            return 0

        pagination_buttons = driver.find_elements(
            By.XPATH, "//button[contains(@class, 'AnchorPaginationsc__Number')]"
        )

        if is_task_cancelled(task_id):
            return 0

        max_page = 1  # Default jika hanya ada 1 halaman
        for button in pagination_buttons:
            try:
                page_num = int(button.text)
                if page_num > max_page:
                    max_page = page_num
            except ValueError:
                continue

        if is_task_cancelled(task_id):
            return 0

        return max_page
    except Exception as e:
        return 1


def collect_job_urls(
    driver, max_page: int, task_id: str, update_progress_func=None
) -> list[str]:
    """Mengumpulkan semua URL pekerjaan"""
    job_urls = []
    progress_data = {}

    if update_progress_func:
        update_progress_func(task_id, "COLLECTING_GLINTS_JOB_URLS", progress_data)

    # for page in range(1, max_page + 1):
    for page in range(1, 2):
        try:
            if is_task_cancelled(task_id):
                break

            url = f"https://glints.com/id/job-category/computer-technology"
            url = f"{url}?page={page}" if page > 1 else url

            driver.get(url)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(3, 5))

            if is_task_cancelled(task_id):
                break

            job_title_tags = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//h2/a[starts-with(@href, '/id/opportunities/jobs/')]")
                )
            )

            if is_task_cancelled(task_id):
                break

            for job_title_tag in job_title_tags:
                job_urls.append(job_title_tag.get_attribute("href"))

            # Update progress
            if update_progress_func:
                update_progress_func(
                    task_id, "COLLECTING_GLINTS_JOB_URLS", progress_data
                )

        except Exception as e:
            pass

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
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[1]/img",
                )
            )
        )

        srcset = img_tag.get_attribute("srcset")
        urls = [item.strip().split(" ") for item in srcset.split(",")]
        url_dict = {int(size[:-1]): url for url, size in urls}
        return url_dict[max(url_dict.keys())]
    except Exception as e:
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
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[2]/div/div[1]/h1",
                )
            )
        )
        return title_tag.get_attribute("textContent").strip()
    except Exception as e:
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
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[2]/div/div[2]/div/a",
                )
            )
        )
        return company_tag.get_attribute("textContent").strip()
    except Exception as e:
        return None


def extract_location(driver, task_id) -> dict[str, str | None] | None:
    """Ekstrak informasi lokasi"""
    if is_task_cancelled(task_id):
        return None

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
        pass

    if is_task_cancelled(task_id):
        return None

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
        pass

    if is_task_cancelled(task_id):
        return None

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
        pass

    return location


def extract_salary(driver, task_id) -> str | None:
    """Ekstrak informasi gaji"""
    if is_task_cancelled(task_id):
        return None

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
        if is_task_cancelled(task_id):
            return None

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
            return None


def extract_employment_details(driver, task_id) -> dict[str, str | None] | None:
    """Ekstrak jenis pekerjaan dan cara kerja"""
    if is_task_cancelled(task_id):
        return None

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
        pass

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
                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[4]",
                )
            )
        )
        return education_tag.get_attribute("textContent").strip()
    except Exception as e:
        return None


def extract_experience(driver, task_id) -> str | None:
    """Ekstrak pengalaman minimum"""
    if is_task_cancelled(task_id):
        return None

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
        return None


def extract_skills(driver, task_id) -> list[str] | None:
    """Ekstrak skill yang dibutuhkan"""
    if is_task_cancelled(task_id):
        return None

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
        return []


def extract_description(driver, task_id) -> str | None:
    """Ekstrak deskripsi pekerjaan"""
    if is_task_cancelled(task_id):
        return None

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
        return None


def extract_job_details(driver, job_url: str, task_id: str) -> dict[str, any] | None:
    """Ekstrak semua detail pekerjaan dari URL"""
    print(f"Scraping detail for: {job_url}")

    if is_task_cancelled(task_id):
        return None

    driver.get(job_url)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(2, 3))

    # Check if task is cancelled after page load
    if is_task_cancelled(task_id):
        return None

    # Ekstrak semua komponen
    img_url = extract_company_logo(driver, task_id)

    # Check cancellation after logo extraction
    if is_task_cancelled(task_id):
        return None

    title = extract_job_title(driver, task_id)

    # Check cancellation after title extraction
    if is_task_cancelled(task_id):
        return None

    company_name = extract_company_name(driver, task_id)

    if is_task_cancelled(task_id):
        return None

    location = extract_location(driver, task_id)

    # Check cancellation after basic info extraction
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

    experience = extract_experience(driver, task_id)

    # Check cancellation before skills and description (heavy operations)
    if is_task_cancelled(task_id):
        return None

    skills = extract_skills(driver, task_id)

    # Final check before description
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
        "scraped_at": datetime.datetime.now().isoformat(),
    }


def scrape_glints_jobs(
    task_id: str, update_state_func=None
) -> tuple[list[dict[str, any]], int] | tuple[list | None]:
    """Fungsi utama untuk scraping data Glints"""
    progress_data = {}

    if is_task_cancelled(task_id):
        return [], None

    # 1. Login dan dapatkan cookies
    update_task_progress(
        task_id, "GETTING_GLINTS_AUTH_DATA", progress_data, update_state_func
    )
    cookies, auth_error = authenticate_to_glints(task_id)

    if auth_error or not cookies:
        return [], None

    if is_task_cancelled(task_id):
        return [], None

    # 2. Inisialisasi driver baru dengan cookies
    driver = get_driver()
    try:
        update_task_progress(
            task_id, "SET_COOKIES_TO_GLINTS", progress_data, update_state_func
        )

        # Set cookies
        driver.get("https://glints.com/id")
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                pass

        if is_task_cancelled(task_id):
            return [], None

        # Refresh dan navigasi
        driver.refresh()
        time.sleep(random.uniform(3, 5))
        driver.get("https://glints.com/id/job-category/computer-technology")

        if is_task_cancelled(task_id):
            close_driver(driver)
            return [], None

        # 3. Dapatkan jumlah halaman
        max_page = get_max_page_number(driver, task_id, update_task_progress)

        if is_task_cancelled(task_id):
            close_driver(driver)
            return [], None

        # 4. Kumpulkan semua URL pekerjaan
        job_urls = collect_job_urls(driver, max_page, task_id, update_task_progress)

        if is_task_cancelled(task_id):
            close_driver(driver)
            return [], None

        # 5. Scrape detail dari setiap URL
        progress_data = {
            "scraped_jobs": 0,
        }
        update_task_progress(
            task_id,
            "SCRAPING_COLLECTED_GLINTS_JOB_DETAIL",
            progress_data,
            update_state_func,
        )

        job_data = []
        for i, job_url in enumerate(job_urls[0:10]):
            if is_task_cancelled(task_id):
                break

            try:
                # Pass task_id to extract_job_details for cancellation checks
                job_detail = extract_job_details(driver, job_url, task_id)

                # Check if job_detail is None (cancelled during extraction)
                if job_detail is None:
                    print(f"Scraping dibatalkan untuk {job_url}")
                    break

                job_data.append(job_detail)

                # Update progress
                progress_data["scraped_jobs"] = len(job_data)
                update_task_progress(
                    task_id,
                    "SCRAPING_COLLECTED_GLINTS_JOB_DETAIL",
                    progress_data,
                    update_state_func,
                )

            except Exception as e:
                pass

        return job_data, len(job_urls)

    except Exception as e:
        return [], None
    finally:
        close_driver(driver)
