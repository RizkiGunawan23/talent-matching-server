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
        chrome_options.add_argument(f"user-agent={get_fake_user_agent()}")
        driver: uc.Chrome = uc.Chrome(options=chrome_options)
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
