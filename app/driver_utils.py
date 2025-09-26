#driver_utils.py
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import random
from app.logging_utils import get_logger
from selenium.webdriver import DesiredCapabilities

logger = get_logger(__name__)


def get_basic_driver(headless=True):
    """Minimal undetectable Chrome driver"""
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"performance": "ALL"} #type: ignore

    driver = Driver(
        browser="chrome",
        headless=headless,
        uc=True,           # Undetected Chrome
        uc_cdp=True,       # helps to access performance logs
        undetectable=True, # SeleniumBase stealth
        window_size="1920, 1080"
    )

    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception as e:
        print(f"Could not enable network CDP: {e}")

    navigator_js = """
    // Remove webdriver property
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    // Set realistic language/platform
    Object.defineProperty(navigator, 'languages', {get: () => ['en-GB','en-US','en']});
    Object.defineProperty(navigator, 'language', {get: () => 'en-GB'});
    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
    """
    try:
        driver.execute_script(navigator_js)
    except Exception as e:
        print(f"Could not execute navigator JS: {e}")
    return driver

def handle_cloudflare_challenge(driver):
    """
    Waits for the chat UI to be ready, implicitly handling Cloudflare challenges.
    This version includes logic to dismiss common pop-ups and modals.
    """
    logger.info("Checking for Cloudflare challenge...")
    try:
        # Define selectors for common elements that indicate the page is ready.
        chat_input_selector = "div.ProseMirror[contenteditable='true']"
        
        # We'll check for any pop-up buttons before the main wait.
        cookie_accept_selector = "button#accept_button"
        
        try:
            # Use find_elements to avoid a NoSuchElementException
            cookie_buttons = driver.find_elements(By.CSS_SELECTOR, cookie_accept_selector)
            if cookie_buttons:
                logger.info("Cookie pop-up found. Attempting to dismiss.")
                # We can assume the first button is the correct one.
                cookie_buttons[0].click()
                # Wait for the pop-up to disappear
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, cookie_accept_selector))
                )
        except Exception:
            # If we fail to dismiss the cookie pop-up, we'll proceed anyway.
            pass

        # Now, wait for the chat input to be present and visible.
        WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, chat_input_selector))
        )
        
        logger.info("SUCCESS: The page is ready for interaction!")
    except TimeoutException:
        logger.error("Timeout: The chat input area was not found. Cloudflare challenge or page load failed.")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while waiting for the chat input: {e}")
        raise