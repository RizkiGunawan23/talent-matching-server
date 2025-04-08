from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium_stealth import stealth
from typing import List
import json
import logging
import os
import random
import re
import time
import undetected_chromedriver as uc

logger = get_task_logger(__name__)


def log_info(message) -> None:
    print(message)
    # logging.info(message)


def get_fake_user_agent() -> str:
    ua = UserAgent()
    return ua.random


def get_driver() -> uc.Chrome | None:
    try:
        chrome_options: uc.ChromeOptions = uc.ChromeOptions()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"user-agent={get_fake_user_agent()}")
        driver: uc.Chrome = uc.Chrome(options=chrome_options)
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True
                )
        return driver
    except Exception as e:
        log_info(f"Error in Driver: {e}")


def close_driver(driver) -> None:
    if driver:
        try:
            driver.quit()
            log_info("Driver berhasil ditutup.")
        except Exception as e:
            log_info(f"Error saat menutup driver: {e}")


def is_task_cancelled(task_id: str) -> bool:
    return cache.get(f"scraping_cancel_{task_id}") == True


@shared_task(bind=True)
def scrape_glints_data_detail(self):
    # logging.basicConfig(
    #     filename="./logs/glints/scraping_glints.log",
    #     level=logging.INFO,
    #     format="%(asctime)s - %(levelname)s - %(message)s",
    #     filemode="w",
    # )

    # Mulai menghitung waktu scraping
    start_time = time.time()
    log_info("Scraping glints dimulai.")

    progress_data = {}
    # Inisialisasi driver
    driver = get_driver()
    try:
        cache.set(
            f'scraping_progress_{self.request.id}', progress_data, timeout=None)
        self.update_state(state="GETTING_AUTH_DATA", meta=progress_data)

        # 1. Buka halaman login Glints
        log_info("Membuka halaman login Glints.")
        driver.get("https://glints.com/id/login")
        log_info("Random sleep.")
        time.sleep(random.uniform(2, 4))

        # 2. Klik tombol "Masuk dengan Email"
        try:
            log_info("Mencari tombol 'Masuk dengan Email'.")
            login_email_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[@aria-label='Login with Email button']"))
            )
            log_info("Klik tombol 'Masuk dengan Email'.")
            login_email_button.click()
        except Exception as e:
            log_info(f"Error di login_email_button: {e}")

        # 3. Isi email dan password
        log_info('Mencari login-form-email')
        email_field = driver.find_element(By.ID, "login-form-email")
        log_info('Mencari login-form-password')
        password_field = driver.find_element(By.ID, "login-form-password")

        log_info('Mengisi login-form-email send key')
        email_field.send_keys("scrapingglints@gmail.com")
        log_info('Mengisi login-form-password send key')
        password_field.send_keys("scrapingglints123")

        # 4. Klik tombol "Masuk"
        log_info('Mencari submit_btn_login')
        submit_button = driver.find_element(
            By.XPATH, "//button[@data-cy='submit_btn_login']")
        log_info('Klik submit_btn_login')
        submit_button.click()

        try:
            log_info('Menentukan login telah berhasil')
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//h1[@class='ForYouTabHeadersc__Heading-sc-vgyvm0-0 euPYjq']"))
            )
        except Exception as e:
            log_info(
                f"Login gagal atau halaman tidak muncul dalam waktu yang cukup: {e}")

        # 5. Simpan cookies setelah login
        log_info('Mengambil cookies')
        cookies = driver.get_cookies()

        # 6. Tutup sesi browser pertama
        close_driver(driver)

        if is_task_cancelled(self.request.id):
            log_info("Task dibatalkan setelah login.")
            close_driver(driver)
            return

        # 7. Buat instance driver baru untuk scraping
        log_info('Membuat instance driver')
        driver = get_driver()

        # 8. Buka halaman utama Glints untuk bisa menambahkan cookies
        log_info('Masuk ke halaman glints/id')
        driver.get("https://glints.com/id")

        # 9. Set cookies ke browser baru
        log_info('Looping cookies')
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                log_info(f"Cookie tidak bisa ditambahkan: {e}")

        # 10. Refresh agar cookies diterapkan
        log_info('Refresh halaman')
        driver.refresh()
        log_info('Random sleep')
        time.sleep(random.uniform(3, 5))

        log_info('Masuk halaman job-category')
        # 11. Navigasi ke halaman kategori pekerjaan tanpa login ulang
        driver.get("https://glints.com/id/job-category/computer-technology")

        cache.set(
            f'scraping_progress_{self.request.id}', progress_data, timeout=None)
        self.update_state(state="GETTING_MAX_PAGE_NUMBER", meta=progress_data)
        # 12. Mencari maksimal page
        log_info('Mencari max page')
        pagination_buttons = driver.find_elements(
            By.XPATH, "//button[contains(@class, 'AnchorPaginationsc__Number')]")

        max_page = 1  # Default jika hanya ada 1 halaman
        log_info('Menghitung max page')
        for button in pagination_buttons:
            try:
                page_num = int(button.text)  # Konversi teks ke integer
                if page_num > max_page:
                    max_page = page_num
                progress_data["max_page"] = max_page
                cache.set(
                    f'scraping_progress_{self.request.id}', progress_data, timeout=None)
                self.update_state(
                    state="GETTING_MAX_PAGE_NUMBER", meta=progress_data)
            except ValueError:
                continue  # Jika teks bukan angka, abaikan

        log_info(f"Halaman terakhir yang tersedia: {max_page}")

        if is_task_cancelled(self.request.id):
            log_info("Task dibatalkan setelah mendapatkan jumlah halaman.")
            close_driver(driver)
            return

        # 13. Looping page selanjutnya sampai akhir
        cache.set(
            f'scraping_progress_{self.request.id}', progress_data, timeout=None)
        self.update_state(
            state="COLLECTING_JOB_URLS", meta=progress_data)
        job_urls: List[str] = []

        # max_page = 1  # Default jika hanya ada 1 halaman saat debugging
        for page in range(1, max_page + 1):
            try:
                if is_task_cancelled(self.request.id):
                    log_info(f"Task dibatalkan saat scraping page ke-{page}.")
                    close_driver(driver)
                    return

                log_info(f'Loop page ke-{page}')
                # 14. Scrape link page untuk detail setiap pekerjaan
                url = f"https://glints.com/id/job-category/computer-technology"
                url = f"{url}?page={page}" if page > 1 else url
                log_info('Navigasi ke halaman')
                driver.get(url)

                log_info('Scrolling halaman')
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                log_info('Random sleep')
                time.sleep(random.uniform(3, 5))

                log_info('Mencari job title tags')
                job_title_tags = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located(
                        (
                            By.XPATH,
                            "//a[starts-with(@href, '/id/opportunities/jobs/')]"
                        )
                    )
                )

                log_info('Memasukkan job urls href ke list')
                for job_title_tag in job_title_tags:
                    try:
                        job_urls.append(job_title_tag.get_attribute("href"))
                        progress_data['total_jobs'] = len(job_urls)
                        cache.set(
                            f'scraping_progress_{self.request.id}', progress_data, timeout=None)
                        self.update_state(
                            state="COLLECTING_JOB_URLS", meta=progress_data)
                    except Exception as e:
                        log_info(f'Error di job_title_tag: {e}')
            except Exception as e:
                log_info(f'Error di job_title_tag looping ke-{page}: {e}')

        job_data: List = []
        i = 0
        log_info(f'Looping job urls {len(job_urls)}')

        cache.set(
            f'scraping_progress_{self.request.id}', progress_data, timeout=None)
        self.update_state(state="SCRAPING_JOB_DETAIL", meta=progress_data)

        for job_url in job_urls:
            # for job_url in job_urls[0:5]:
            # 15. Scrape detail pekerjaan di setiap link
            try:
                if is_task_cancelled(self.request.id):
                    log_info(f"Task dibatalkan saat scraping job detail.")
                    close_driver(driver)
                    return

                log_info(f'get job detail loop {i}')
                log_info('get job detail')
                driver.get(job_url)
                i += 1

                log_info('scroll')
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                log_info('random sleep')
                time.sleep(random.uniform(2, 3))

                img_url = None
                try:
                    # 16. Mencari tag yang berisi informasi link gambar
                    log_info('search image tags')
                    img_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[1]/img"
                            )
                        )
                    )

                    srcset = img_tag.get_attribute("srcset")

                    urls = [item.strip().split(" ")
                            for item in srcset.split(",")]

                    # Ubah ke dict dengan ukuran sebagai key dan URL sebagai value
                    url_dict = {int(size[:-1]): url for url, size in urls}

                    # Ambil URL terbesar
                    img_url = url_dict[max(url_dict.keys())]
                except Exception as e:
                    log_info(f'Error di img_tag: {e}')
                    img_url = "https://img.icons8.com/?size=720&id=53373&format=png&color=000000"

                title = None
                try:
                    # 17. Mencari tag yang berisi informasi judul pekerjaan
                    log_info('search title tag')
                    title_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[2]/div/div[1]/h1"
                            )
                        )
                    )

                    log_info('get title text')
                    title = title_tag.get_attribute("textContent").strip()
                except Exception as e:
                    log_info(f'Error di job_title_tag: {e}')

                company_name = None
                try:
                    # 18. Mencari tag yang berisi informasi nama perusahaan
                    log_info('search company name tag')
                    company_name_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[1]/div[2]/div/div[2]/div/a"
                            )
                        )
                    )

                    log_info('get company name text')
                    company_name = company_name_tag.get_attribute(
                        "textContent").strip()
                except Exception as e:
                    log_info(f'Error di company_name_tag: {e}')

                subdistrict = None
                try:
                    # 19. Mencari tag yang berisi informasi kecamatan/kabupaten
                    log_info('search subdistrict tag')
                    subdistrict_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[1]/div/label[5]/a"
                            )
                        )
                    )

                    log_info('get subdistrict text')
                    subdistrict = subdistrict_tag.get_attribute(
                        "textContent").strip()
                except Exception as e:
                    log_info(f'Error di subdistrict_tag: {e}')

                city = None
                try:
                    # 20. Mencari tag yang berisi informasi kota
                    log_info('search city tag')
                    city_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[1]/div/label[4]/a"
                            )
                        )
                    )

                    log_info('get city text')
                    city = city_tag.get_attribute(
                        "textContent").strip()
                except Exception as e:
                    log_info(f'Error di city_tag: {e}')

                province = None
                try:
                    # 21. Mencari tag yang berisi informasi provinsi
                    log_info('search province tag')
                    province_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[1]/div/label[3]/a"
                            )
                        )
                    )

                    log_info('get province text')
                    province = province_tag.get_attribute(
                        "textContent").strip()
                except Exception as e:
                    log_info(f'Error di province_tag: {e}')

                salary = None
                try:
                    # 22. Mencari tag yang berisi informasi gaji
                    log_info('search salary tags')
                    salary_tag_container = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[1]/div/span"
                            )
                        )
                    )

                    log_info('get salary text')
                    salary = salary_tag_container.get_attribute(
                        "textContent").strip()

                    if len(re.findall(r'[\d\.]+', salary)) == 0:
                        salary = None
                except Exception as e:
                    log_info(f'Error di salary_tag_container: {e}')
                    try:
                        # 22.a Mencari tag yang berisi informasi gaji dengan xpath lain
                        log_info('search salary tags with different xpath')
                        salary_tag_container = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[1]"
                                )
                            )
                        )

                        log_info('get salary text with different xpath')
                        salary = salary_tag_container.get_attribute(
                            "textContent").strip()

                        if len(re.findall(r'[\d\.]+', salary)) == 0:
                            salary = None
                    except Exception as e:
                        log_info(
                            f'Error di salary_tag_container with different xpath: {e}')

                employment_type = None
                work_setup = None
                try:
                    # 23. Mencari tag yang berisi informasi jenis pekerjaan dan cara kerja
                    log_info('search employment type and work setup tag')
                    employment_type_and_work_setup_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[3]"
                            )
                        )
                    )

                    log_info('get employment type and work setup text')
                    employment_type_and_work_setup_text = employment_type_and_work_setup_tag.get_attribute(
                        "textContent").strip()

                    employment_type_and_work_setup_text = employment_type_and_work_setup_text.split(
                        ' · ')
                    employment_type = employment_type_and_work_setup_text[0]
                    work_setup = employment_type_and_work_setup_text[1]
                except Exception as e:
                    log_info(
                        f'Error di employment_type_and_work_setup_tag: {e}')

                minimum_education = None
                try:
                    # 24. Mencari tag yang berisi informasi minimal pendidikan
                    log_info('search minimum education tag')
                    minimum_education_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[4]"
                            )
                        )
                    )

                    log_info('get minimum education text')
                    minimum_education = minimum_education_tag.get_attribute(
                        "textContent").strip()
                except Exception as e:
                    log_info(f'Error di minimum_education_tag: {e}')

                minimum_experience = None
                try:
                    # 25. Mencari tag yang berisi informasi minimal pengalaman
                    log_info('search minimum experience tag')
                    minimum_experience_tag = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[2]/div/div[1]/div[2]/div[2]/div[2]/div/main/div[3]/div[5]"
                            )
                        )
                    )

                    log_info('get minimum experience text')
                    minimum_experience = minimum_experience_tag.get_attribute(
                        "textContent").strip()

                    minimum_experience = minimum_experience if 'pengalaman' in minimum_experience.lower() else None

                except Exception as e:
                    log_info(f'Error di minimum_experience_tag: {e}')

                required_skills = None
                try:
                    # 26. Mencari tag yang berisi informasi skill yang dibutuhkan
                    log_info('search required skills container')
                    required_skills_container = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "//div[contains(@class, 'Opportunitysc__SkillsContainer-sc-gb4ubh-10 jccjri')]"
                            )
                        )
                    )

                    log_info('wait for required skills tags to load')
                    time.sleep(random.uniform(2, 3))
                    log_info('find required skills tags')
                    required_skills_tags = required_skills_container.find_elements(
                        By.TAG_NAME, "label"
                    )

                    log_info('get required skills text')
                    required_skills = [required_skill_tag.get_attribute(
                        "textContent").strip() for required_skill_tag in required_skills_tags]
                except Exception as e:
                    log_info(f'Error di required_skills_tag: {e}')

                job_description = None
                try:
                    # 27. Mencari tag yang berisi informasi deskripsi pekerjaan
                    log_info('search job description container')
                    job_description_container = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (By.XPATH,
                             "//div[contains(@class, 'DraftjsReadersc__ContentContainer-sc-zm0o3p-0 pVRwR')]")
                        )
                    )

                    log_info('get job description innerHTML')
                    job_description = job_description_container.get_attribute(
                        "innerHTML")
                except Exception as e:
                    log_info(f'Error di job_description_tag: {e}')

                log_info('append new job data')
                job_data.append(
                    {
                        "job_url": job_url,
                        "image_url": img_url,
                        "job_title": title,
                        "company_name": company_name,
                        "subdistrict": subdistrict,
                        "city": city,
                        "province": province,
                        "salary": salary,
                        "employment_type": employment_type,
                        "work_setup": work_setup,
                        "minimum_education": minimum_education,
                        "minimum_experience": minimum_experience,
                        "required_skills": required_skills,
                        "job_description": job_description,
                    }
                )

                progress_data["scraped_jobs"] = len(job_data)

                cache.set(
                    f'scraping_progress_{self.request.id}', progress_data, timeout=None)
                self.update_state(
                    state="SCRAPING_JOB_DETAIL", meta=progress_data)

            except Exception as e:
                log_info(f'Error di job_url: {e}')

        close_driver(driver)

        return job_data

    except Exception as e:
        log_info(f'Error di proses scraping: {e}')
        close_driver(driver)
