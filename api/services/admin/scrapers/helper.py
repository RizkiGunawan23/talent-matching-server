import undetected_chromedriver as uc
from django.core.cache import cache
from fake_useragent import UserAgent
from selenium_stealth import stealth


def get_fake_user_agent() -> str:
    ua = UserAgent()
    return ua.random


def get_driver() -> uc.Chrome | None:
    try:
        chrome_options: uc.ChromeOptions = uc.ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        chrome_options.add_argument("--ignore-ssl-errors-list")
        chrome_options.add_argument(f"user-agent={get_fake_user_agent()}")
        driver: uc.Chrome = uc.Chrome(
            options=chrome_options,
            version_main=136,
            driver_executable_path=None,
        )
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver
    except Exception as e:
        print(f"Error in Driver: {e}")


def close_driver(driver) -> None:
    if driver:
        try:
            driver.quit()
            print("Driver berhasil ditutup.")
        except Exception as e:
            print(f"Error saat menutup driver: {e}")


def is_task_cancelled(task_id: str) -> bool:
    return cache.get(f"scraping_cancel_{task_id}") == True


def add_cookie_safely(driver, cookie):
    """Safely add cookie with domain validation"""
    try:
        current_url = driver.current_url
        current_domain = (
            current_url.split("/")[2] if "//" in current_url else current_url
        )

        # Clean domain from cookie
        if "domain" in cookie:
            cookie_domain = cookie["domain"].lstrip(".")
            if cookie_domain not in current_domain:
                print(
                    f"Skipping cookie with domain mismatch: {cookie_domain} vs {current_domain}"
                )
                return False

        driver.add_cookie(cookie)
        return True
    except Exception as e:
        print(f"Failed to add cookie: {e}")
        return False


def update_task_progress(
    task_id: str, state: str, progress_data: dict[str, any], update_state_func=None
):
    """Update progres task di cache dan celery state"""
    cache.set(f"scraping_progress_{task_id}", progress_data, timeout=None)
    if update_state_func:
        update_state_func(state=state, meta=progress_data)
