# run_headless_check.py
import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
from app.logging_utils import get_logger
import random
from selenium.webdriver.common.keys import Keys 
logger = get_logger(__name__)



def human_like_scroll(driver, scroll_pause_range=(0.1,0.3), max_scrolls=10):
    """
    Simulates human-like scrolling behavior on the page.
    """
    last_height = driver.execute_script("return window.scrollY || 0;")
    viewport_height = driver.execute_script("return window.innerHeight;")
    
    for i in range(max_scrolls):
        # Scroll a random fraction of the viewport
        scroll_amount = random.randint(int(viewport_height*0.3), int(viewport_height*0.7))
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        # Pause like a human reading
        time.sleep(random.uniform(*scroll_pause_range))
        
        new_height = driver.execute_script("return window.scrollY || 0;")
        if new_height == last_height:
            # Reached bottom
            break
        last_height = new_height

def human_like_hover(driver,element):
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(random.uniform(0.2, 0.6))  # small hesitation
    actions.perform()

def human_like_typing(element, text, min_delay=0.05, max_delay=0.15):
    """
    Types text into a contenteditable element like a human.
    
    element: Selenium WebElement (the input box)
    text: string to type
    min_delay, max_delay: delay between keystrokes
    """
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))
    element.send_keys(Keys.ENTER)  # send the message

def add_human_like_behavior(driver):
    """
    Adds human-like behavior: wait, scroll, small pauses, optional hover.
    """
    # Wait for page to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(random.uniform(2, 5))  # random initial pause

    # Incremental scrolling
    human_like_scroll(driver, scroll_pause_range=(0.2, 0.5), max_scrolls=15)
    
    # Optional: small random scroll back up to simulate reading
    if random.random() < 0.5:
        driver.execute_script(f"window.scrollBy(0, {-random.randint(50, 200)});")
        time.sleep(random.uniform(0.2, 0.5))

    # Optional: hover over a random element
    if random.random() < 0.5:
        elements = driver.find_elements(By.CSS_SELECTOR, "div.markdown.prose")
        if elements:
            random_element = random.choice(elements)
            human_like_hover(driver, random_element)

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

