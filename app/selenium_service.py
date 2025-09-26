#selenium_service.py
import time
import re
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from app.logging_utils import get_logger
from app.driver_utils import handle_cloudflare_challenge, get_basic_driver
import json
logger = get_logger(__name__)

CHATGPT_URL = "https://chat.openai.com/"


def submit_prompt(driver, prompt: str, wait_secs: int = 45, min_delay: float = 0.05, max_delay: float = 0.15):
    """
    Submit a prompt into ChatGPT's contenteditable ProseMirror div using Selenium,
    simulating human-like typing.

    Args:
        driver: Selenium WebDriver instance
        prompt: string to submit
        wait_secs: maximum wait for input box to appear
        min_delay, max_delay: per-character typing delay range
    """
    try:
        logger.info(f"Submitting prompt: '{prompt[:50]}...'")

        # Wait for the input area to be visible
        input_box = WebDriverWait(driver, wait_secs).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']"))
        )

        # Scroll into view
        driver.execute_script("arguments[0].scrollIntoView(true);", input_box)
        time.sleep(random.uniform(0.05, 0.15))

        # Optional small hover
        ActionChains(driver).move_to_element(input_box).pause(random.uniform(0.1, 0.3)).perform()

        # Clear any existing text
        input_box.send_keys(Keys.CONTROL, "a")
        input_box.send_keys(Keys.DELETE)
        time.sleep(random.uniform(0.05, 0.1))

        # Type the prompt character by character with randomized delays
        for ch in prompt:
            input_box.send_keys(ch)
            time.sleep(random.uniform(min_delay, max_delay))

        # Small pause before pressing Enter (human hesitation)
        time.sleep(random.uniform(0.2, 0.5))
        input_box.send_keys(Keys.RETURN)

        logger.info("Prompt submitted successfully")
        return True

    except TimeoutException:
        logger.error("Prompt submission failed: input area not found")
        return False
    except ElementNotInteractableException:
        logger.error("Prompt submission failed: element not interactable")
        return False
    except Exception as e:
        logger.error(f"Failed to submit prompt: {e}")
        raise

def clean_answer(answer: str) -> str:
    """Clean up the answer text."""
    text = re.sub(r"\s*\n\s*", " ", answer)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def check_for_block(driver, timeout=5):
    """
    Uses Chrome DevTools Protocol (CDP) to detect 403 Forbidden responses.
    Returns True if a block is detected, otherwise False.

    Args:
        driver: SeleniumBase driver instance
        timeout: How many seconds to poll for responses

    Returns:
        bool
    """
    import time

    try:
        # Enable network tracking via CDP
        driver.execute_cdp_cmd("Network.enable", {})

        # Poll for a few seconds to catch any immediate 403 responses
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Get all current requests/responses from the browser
            # Note: responseReceived events contain status codes
            # SeleniumBase does not provide a direct API for CDP event stream,
            # so we use execute_cdp_cmd with "Network.getResponseBody" for each request if needed.
            # Here, we can inspect the page for a Cloudflare block element as a fallback
            page_text = driver.find_element("tag name", "body").text
            if "403" in page_text or "access denied" in page_text.lower():
                return True
            time.sleep(0.2)

        return False

    except Exception as e:
        print(f"Warning: Could not check for block via CDP ({e})")
        return False

def get_response(driver):
    """
    Waits for the full response to appear and retrieves the text.
    Uses robust polling to monitor text stability, and checks for Cloudflare 403 blocks.

    Args:   
        driver (selenium.webdriver): The WebDriver instance.

    Returns:
        str or dict: The complete text of the chatbot's response,
                     or a structured error if blocked or failed.
    """
    import time
    try:
        print("Waiting for response to start streaming...")

        # --- Check for Cloudflare block or 403 page immediately ---
        if check_for_block(driver):
            return {"status": "error", "code": 403}

        # --- Phase 1: Wait for the assistant message container ---
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.markdown.prose"))
            )
        except TimeoutException:
            print("Timeout while waiting for message container.")
            return {"status": "error",
                    "message": "Timeout occurred while waiting for message container.",
                    "code": 408}

        print("Assistant message container found.")

        # --- Phase 2: Poll text for stabilization ---
        state = {
            "last_text_length": 0,
            "stabilization_count": 0
        }

        def stable_text_poll(d):
            """Internal polling function for WebDriverWait."""
            # Optional: early check for block mid-stream
            if check_for_block(d):
                raise Exception("Blocked by 403 during streaming")

            last_message_elements = d.find_elements(By.CSS_SELECTOR, "div.markdown.prose")
            if not last_message_elements:
                return False

            current_text = last_message_elements[-1].text.strip()
            print(f"Current length={len(current_text)} | StableCount={state['stabilization_count']}")

            if len(current_text) > 0 and len(current_text) == state['last_text_length']:
                state['stabilization_count'] += 1
                if state['stabilization_count'] >= 2:
                    return True
            else:
                state['stabilization_count'] = 0

            state['last_text_length'] = len(current_text)
            return False

        # Poll until text stabilizes (or max 90 seconds)
        WebDriverWait(driver, 90, 0.5).until(stable_text_poll)

        # --- Phase 3: Return final stabilized text ---
        final_message_element = driver.find_elements(By.CSS_SELECTOR, "div.markdown.prose")[-1]
        raw_text = final_message_element.text.strip()
        cleaned_text = clean_answer(raw_text)
        print("Response stabilized and retrieved.")
        return cleaned_text

    except TimeoutException:
        print("Timeout: The chatbot took too long to respond.")
        return {"status": "error",
                "message": "Timeout waiting for response.",
                "code": 504}
    
    except NoSuchElementException:
        print("Error: Could not find a required element on the page.")
        return {"status": "error", 
                "message": "Element not found.",
                "code": 404}
    
    except Exception as e:
        # Check if it was a 403 detected mid-stream
        if str(e).lower().startswith("blocked by 403"):
            return {"status": "error", "code": 403}
        print(f"Error: An unexpected error occurred: {e}")
        return {"status": "error", 
                "message": f"Unexpected error: {e}",
                "code": 500}

def check_text_stabilization(driver, state):
    """
    Checks if the text of the last assistant message has stabilized.
    This function is designed to be used with WebDriverWait.
    """
    try:
        last_message_elements = driver.find_elements(By.CSS_SELECTOR, "div.markdown.prose")
        if not last_message_elements:
            return False

        current_text = last_message_elements[-1].text.strip()
        print(f"Current length={len(current_text)} | StableCount={state['stabilization_count']}")
        
        # Check if the text is present and its length has stabilized.
        if len(current_text) > 0 and len(current_text) == state['last_text_length']:
            state['stabilization_count'] += 1
            if state['stabilization_count'] >= 2:
                return True
        else:
            state['stabilization_count'] = 0

        state['last_text_length'] = len(current_text)
        return False

    except IndexError:
        return False
    except Exception:
        return False

def wait_for_initial_response(driver, timeout: int = 60):
    """
    Waits for the initial message bubble to appear after a prompt is submitted.
    This is a critical step to ensure the server has begun to respond.
    """
    logger.info("Waiting for initial response message...")
    message_selector = "div.markdown.prose"
    try:
        # Wait until there are at least 2 message bubbles (user + assistant)
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, message_selector)) >= 2
        )
        logger.info("Initial response detected.")
    except (TimeoutException, NoSuchElementException) as e:
        logger.warning(f"Timeout or element not found during initial wait: {e}")
        # Re-raise the exception to be handled by the main retry logic.
        raise
        
def wait_for_page_load(driver, timeout_sec: int = 60):
    """Waits for the page to be fully loaded by checking for the body tag."""
    try:
        WebDriverWait(driver, timeout_sec).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        logger.info("Page loaded.")
    except TimeoutException:
        logger.error("Page failed to load within the given timeout.")
        raise

def get_chatgpt_answer(prompt: str) -> str:
    """
    High-level function: open browser -> send prompt -> get response -> quit.
    Includes a retry mechanism for robust operation.
    """
    # Change 1: Increased max_retries to a sensible value for robustness.
    max_retries = 1
    for attempt in range(1, max_retries + 1):
        driver = None
        try:
            logger.info(f"Starting ChatGPT automation flow (Attempt {attempt} of {max_retries})")
            
            # STEP 1: Initialize the undetectable browser
            driver = get_basic_driver()
            if driver is None:
                logger.error(f"Failed to initialize driver on attempt {attempt}.")
                continue # Skip to the next attempt in the loop
            
            # STEP 2: Navigate and handle page modals/challenges
            driver.get(CHATGPT_URL)
            # Handle the Cloudflare challenge immediately upon navigation.
            handle_cloudflare_challenge(driver)
            # Then, perform human-like behavior on the main chat page.
            # STEP 3: Submit the prompt and get the answer
            submit_prompt(driver, prompt)
    
            # get_response now raises an exception on failure, which is caught below.
            answer = get_response(driver)
            # If we reach this point, the response was successful.
            logger.info("Received valid response from ChatGPT")
            return answer
            
        except Exception as e:
            # The get_response function now raises an exception for failures.
            # This is a cleaner way to handle retries.
            logger.error(f"Error in ChatGPT flow on attempt {attempt}: {e}")
            
        finally:
            if driver:
                #driver.quit()
                logger.info("Browser closed")
        
        time.sleep(2) # Wait 2 seconds before the next retry
        
    logger.error(f"Failed to get a response after {max_retries} attempts.")
    return "Error: Failed to get response after multiple attempts"