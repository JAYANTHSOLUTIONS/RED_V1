import json
import os
import time
from io import BytesIO

from PIL import Image, ImageFilter
import pytesseract
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    NoSuchWindowException,
    StaleElementReferenceException,
    TimeoutException,
    UnexpectedAlertPresentException,
)
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

import argparse
import shutil

# Configure Tesseract path for Windows & environment
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
elif shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

# Configuration variables
MOBILE_NUMBER = os.getenv("TNGIS_MOBILE")
PASSWORD = os.getenv("TNGIS_PASSWORD")

parser = argparse.ArgumentParser(description="TNGIS Land & Revenue Scraper")
parser.add_argument("--district", default=os.getenv("TNGIS_DISTRICT", "Kancheepuram"))
parser.add_argument("--taluk", default=os.getenv("TNGIS_TALUK", "Walajabad"))
parser.add_argument("--village", default=os.getenv("TNGIS_VILLAGE", "Walajabad"))
parser.add_argument("--survey", default=os.getenv("TNGIS_SURVEY_NO", "217"))
parser.add_argument("--subdiv", default=os.getenv("TNGIS_SUB_DIV", "1B2"))
parser.add_argument("--area-type", default=os.getenv("TNGIS_AREA_TYPE", "rural"))
parser.add_argument("--output", default="tngis_map_results.txt", help="Path to save output results file")
parser.add_argument("--session-id", default=None, help="Session ID for live status tracking")
parser.add_argument("--non-interactive", action="store_true", help="Bypass manual map pin prompt")
parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
args, _ = parser.parse_known_args()

TARGET_DISTRICT = args.district
TARGET_TALUK = args.taluk
TARGET_VILLAGE = args.village
TARGET_SURVEY_NO = args.survey
TARGET_SUB_DIV = args.subdiv
AREA_TYPE = args.area_type
NON_INTERACTIVE = args.non_interactive
IS_HEADLESS = args.headless
OUTPUT_FILE = args.output
SESSION_ID = args.session_id

STATUS_FILE = f"tngis_status_{SESSION_ID}.json" if SESSION_ID else None
SIGNAL_FILE = f"tngis_continue_{SESSION_ID}.signal" if SESSION_ID else None


def update_status(status_str, message, extra=None):
    """Write live process state to status file for backend / frontend tracking."""
    if not STATUS_FILE:
        return
    data = {
        "session_id": SESSION_ID,
        "status": status_str,
        "message": message,
        "timestamp": time.time(),
    }
    if extra:
        data.update(extra)
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as sf:
            json.dump(data, sf)
    except Exception as exc:
        print(f"Status update error: {exc}")
PORTAL_URL = "https://tngis.tn.gov.in/apps/gi_viewer/map-viewer/index.html"
CAPTCHA_IMAGE_XPATH = (
    "//*[@id='publicCaptchaImage']"
    " | //*[@id='publicCaptcha']"
    " | //img[contains(translate(@id, 'CAPTCHA', 'captcha'), 'captcha')]"
    " | //img[contains(translate(@src, 'CAPTCHA', 'captcha'), 'captcha')]"
)


def extract_captcha_text(driver):
    """Read the visible CAPTCHA image and return its alphanumeric text."""
    try:
        captcha_image = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.XPATH, CAPTCHA_IMAGE_XPATH))
        )
        image = Image.open(BytesIO(captcha_image.screenshot_as_png))
        image = image.resize(
            (image.width * 3, image.height * 3),
            Image.Resampling.LANCZOS,
        )
        image = image.convert("L")
        image = image.point(lambda pixel: 255 if pixel > 140 else 0)
        image = image.filter(ImageFilter.SHARPEN)

        config = (
            r"--psm 6 -c "
            r"tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
        return "".join(pytesseract.image_to_string(image, config=config).split())
    except Exception as error:
        print(f"OCR CAPTCHA extraction failed: {error}")
        return ""


def dismiss_alert_if_present(driver, timeout=2):
    """Accept a portal alert and return its message, if one appears."""
    try:
        alert = WebDriverWait(driver, timeout).until(EC.alert_is_present())
        message = alert.text
        alert.accept()
        return message
    except Exception:
        return ""


def click_if_present(driver, xpath, timeout=5):
    """Click an element when available and return whether it was found."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].click();", element)
        return True
    except (NoSuchWindowException, TimeoutException, StaleElementReferenceException):
        return False


def extract_text_if_present(driver, xpath, timeout=8):
    """Return visible text from an element, or an empty string if unavailable."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
        )
        return element.text.strip()
    except (NoSuchWindowException, TimeoutException, StaleElementReferenceException):
        return ""


def extract_dom_text_if_present(driver, xpath, timeout=8):
    """Read DOM text even when the target element is hidden by the portal UI."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return driver.execute_script(
            "return (arguments[0].innerText || arguments[0].textContent || '').trim();",
            element,
        )
    except (TimeoutException, StaleElementReferenceException):
        return ""


def extract_panel_data(driver, child_xpath, container_xpath='//*[@id="areg-tab-container"]', timeout=20):
    """Wait for tab content and collect text plus values from rendered form controls."""
    ignored_headings = {"# owner relative relation", "# land information"}
    deadline = time.time() + timeout
    best_text = ""

    while time.time() < deadline:
        try:
            child = driver.find_element(By.XPATH, child_xpath)
            container = driver.find_element(By.XPATH, container_xpath)
            text = driver.execute_script(
                """
                const root = arguments[0];
                const chunks = [root.innerText || root.textContent || ''];
                root.querySelectorAll('input, textarea, select').forEach((element) => {
                    if (element.tagName === 'SELECT') {
                        const option = element.options[element.selectedIndex];
                        if (option && option.textContent.trim()) chunks.push(option.textContent);
                    } else if (element.value && element.value.trim()) {
                        chunks.push(element.value);
                    }
                });
                return chunks.join('\\n').replace(/\\n{3,}/g, '\\n\\n').trim();
                """,
                container,
            )
            child_text = child.get_attribute("innerText") or ""
            combined = "\n".join(part.strip() for part in (text, child_text) if part.strip())
            lines = [line.strip() for line in combined.splitlines() if line.strip()]
            meaningful = [line for line in lines if line.casefold() not in ignored_headings]
            if len("\n".join(meaningful)) > len(best_text):
                best_text = "\n".join(meaningful)
            if meaningful:
                return best_text
        except (NoSuchElementException, NoSuchWindowException, StaleElementReferenceException):
            pass
        time.sleep(0.5)

    return best_text


def element_exists(driver, xpath, timeout=5):
    """Return whether an element exists, regardless of whether it is clickable."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return True
    except (TimeoutException, NoSuchWindowException):
        return False


def wait_for_panel_loading(driver, timeout=3):
    """Wait for the map information panel's loading overlay to disappear with fast polling."""
    loading_xpath = "//*[contains(@class, 'loading') or contains(@id, 'loading') or contains(@class, 'spinner')]"
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.1).until(
            lambda current_driver: not any(
                element.is_displayed()
                for element in current_driver.find_elements(By.XPATH, loading_xpath)
            )
        )
    except Exception:
        pass


def click_first_available(driver, xpaths, timeout=5):
    """Click the first available control from a list of equivalent selectors."""
    for xpath in xpaths:
        if click_if_present(driver, xpath, timeout):
            return True
    return False


def save_result_section(results_file, title, text):
    """Append a labelled extraction section to the results file."""
    results_file.write(f"\n{'=' * 50}\n{title}\n{'=' * 50}\n")
    results_file.write(text or "[No data extracted]\n")
    results_file.write("\n")

# WebDriver Initialization
print(f"[TNGIS] Initializing browser (headless={IS_HEADLESS})...")
update_status("starting", "Launching optimized Chrome engine...")
options = webdriver.ChromeOptions()
options.page_load_strategy = 'eager'  # Proceed as soon as DOM is interactive
if IS_HEADLESS:
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--dns-prefetch-disable")
else:
    options.add_argument("--start-maximized")

try:
    driver = webdriver.Chrome(options=options)
except Exception as init_err:
    print(f"[TNGIS] Direct Chrome launch fallback: {init_err}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

wait = WebDriverWait(driver, 20)

try:
    print(f"[TNGIS] Navigating to {PORTAL_URL} for Survey {TARGET_SURVEY_NO}/{TARGET_SUB_DIV} in {TARGET_VILLAGE}, {TARGET_TALUK}...")
    update_status("logging_in", "Connecting to TNGIS map viewer and solving CAPTCHA via OCR...")
    # 1. Open target portal
    driver.get(PORTAL_URL)

    # 2. Click Existing User / Proceed Login and ensure CAPTCHA loaded
    captcha_input = None
    for attempt in range(1, 4):
        try:
            btn_proceed = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btnProceedLogin"]')))
            btn_proceed.click()
            captcha_input = WebDriverWait(driver, 8).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="publicCaptchaInput"]'))
            )
        except (TimeoutException, UnexpectedAlertPresentException):
            alert_message = dismiss_alert_if_present(driver)
            if "captcha" not in alert_message.lower():
                raise
            print(f"CAPTCHA load failed (attempt {attempt}/3); refreshing the page...")
            driver.refresh()
            continue

        alert_message = dismiss_alert_if_present(driver)
        if "captcha" in alert_message.lower() and "failed" in alert_message.lower():
            print(f"CAPTCHA load failed (attempt {attempt}/3); refreshing the page...")
            driver.refresh()
            continue
        break
    else:
        raise RuntimeError("The portal could not load a CAPTCHA after 3 refresh attempts.")

    # 3. Fill Mobile / Identifier
    field_user = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="publicIdentifier"]')))
    field_user.clear()
    field_user.send_keys(MOBILE_NUMBER)

    # 4. Fill Password
    field_pass = driver.find_element(By.XPATH, '//*[@id="publicPassword"]')
    field_pass.clear()
    field_pass.send_keys(PASSWORD)

    # 5. Extract and submit CAPTCHA, retrying with a fresh image when rejected
    if captcha_input is None:
        raise RuntimeError("CAPTCHA input was not available after the login form loaded.")
    login_succeeded = False
    for login_attempt in range(1, 6):
        if login_attempt > 1:
            try:
                captcha_image = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, CAPTCHA_IMAGE_XPATH))
                )
                driver.execute_script("arguments[0].click();", captcha_image)
                time.sleep(1)
                dismiss_alert_if_present(driver)
            except TimeoutException:
                try:
                    driver.get(PORTAL_URL)
                    dismiss_alert_if_present(driver)
                    WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="btnProceedLogin"]'))
                    ).click()
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="publicIdentifier"]'))
                    ).send_keys(MOBILE_NUMBER)
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="publicPassword"]'))
                    ).send_keys(PASSWORD)
                except TimeoutException:
                    print("Login form did not reopen; trying the next CAPTCHA attempt...")
                    continue
            try:
                captcha_input = wait.until(
                    EC.visibility_of_element_located((By.XPATH, '//*[@id="publicCaptchaInput"]'))
                )
            except TimeoutException:
                alert_message = dismiss_alert_if_present(driver)
                print(f"CAPTCHA form reload failed: {alert_message or 'no form found'}")
                continue

        captcha_text = extract_captcha_text(driver)
        if not captcha_text:
            if not NON_INTERACTIVE:
                print("OCR could not read this CAPTCHA. Type the visible CAPTCHA to continue.")
                captcha_text = input("CAPTCHA: ").strip()
                if not captcha_text:
                    raise RuntimeError("No CAPTCHA value was entered.")
            else:
                print("OCR could not read this CAPTCHA; retrying next attempt...")
                continue

        print(f"OCR CAPTCHA text (attempt {login_attempt}/5): {captcha_text}")
        captcha_input.clear()
        captcha_input.send_keys(captcha_text)
        driver.find_element(By.XPATH, '//*[@id="publicLoginBtn"]').click()
        time.sleep(1)

        login_alert = dismiss_alert_if_present(driver)
        if login_alert:
            if "captcha" in login_alert.lower():
                print("CAPTCHA rejected; requesting a fresh image...")
                continue
            raise RuntimeError(f"Portal login failed: {login_alert}")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="offcanvasScrolling-right"]'))
            )
            login_succeeded = True
            break
        except TimeoutException:
            if driver.find_elements(By.XPATH, '//*[@id="publicLoginBtn"]'):
                print("Login did not complete; retrying with a fresh CAPTCHA...")
                continue
            raise RuntimeError("The map controls did not load after login.")

    if not login_succeeded:
        raise RuntimeError("Login failed after 5 CAPTCHA attempts.")

    # 6. Area Type Selection (Urban / Rural)

    # 6. Area Type Selection (Urban / Rural)
    area_type = AREA_TYPE.lower()
    area_label_xpath = (
        "//*[@id='offcanvasScrolling-right']//*[self::label or self::button or self::input]["
        f"contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{area_type}') "
        f"or contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{area_type}') "
        f"or contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{area_type}') "
        "]"
    )
    area_input_xpath = (
        "//*[@id='offcanvasScrolling-right']//input["
        "translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')="
        f"'{area_type}']"
    )

    try:
        area_control = wait.until(EC.presence_of_element_located((By.XPATH, area_input_xpath)))
        driver.execute_script("arguments[0].click();", area_control)
    except TimeoutException as error:
        try:
            area_control = wait.until(EC.element_to_be_clickable((By.XPATH, area_label_xpath)))
            driver.execute_script("arguments[0].click();", area_control)
        except TimeoutException:
            controls = driver.find_elements(
                By.XPATH,
                '//*[@id="offcanvasScrolling-right"]//*[self::label or self::button or self::input]',
            )
            control_summary = [
                f"{control.tag_name} id={control.get_attribute('id')!r} "
                f"value={control.get_attribute('value')!r} text={control.text.strip()!r}"
                for control in controls
            ]
            raise RuntimeError(
                f"Could not find the {area_type} area control. Available controls: {control_summary}"
            ) from error

    # Helper function for dropdown selection
    def select_option(xpath, visible_text):
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            # Wait until dropdown options are populated via AJAX with fast polling.
            WebDriverWait(driver, 12, poll_frequency=0.1).until(
                lambda current_driver: len(
                    Select(current_driver.find_element(By.XPATH, xpath)).options
                ) > 1
            )
        except TimeoutException as error:
            selects = driver.find_elements(By.TAG_NAME, "select")
            select_summary = [
                f"id={select_element.get_attribute('id')!r} "
                f"name={select_element.get_attribute('name')!r} "
                f"options={len(Select(select_element).options)}"
                for select_element in selects
            ]
            raise RuntimeError(
                f"Dropdown {xpath} did not load. Available selects: {select_summary}"
            ) from error

        select_element = driver.find_element(By.XPATH, xpath)
        select = Select(select_element)
        target_text = visible_text.strip().casefold()
        if target_text == "any":
            matching_option = next(
                (
                    option
                    for option in select.options
                    if (option.get_attribute("value") or "").strip() not in {"", "0", "-1"}
                ),
                None,
            )
        else:
            matching_option = next(
                (
                    option
                    for option in select.options
                    if any(
                        candidate.strip().casefold() == target_text
                        for candidate in (
                            option.text,
                            option.get_attribute("textContent") or "",
                            option.get_attribute("value") or "",
                        )
                    )
                ),
                None,
            )
        if matching_option is None:
            raise RuntimeError(
                f"Option {visible_text!r} was not found in {xpath}. "
                f"Available options: "
                f"{[(option.text.strip(), option.get_attribute('textContent'), option.get_attribute('value')) for option in select.options]}"
            )
        option_value = matching_option.get_attribute("value")
        driver.execute_script(
            """
            const select = arguments[0];
            const value = arguments[1];
            select.value = value;
            select.dispatchEvent(new Event('input', {bubbles: true}));
            select.dispatchEvent(new Event('change', {bubbles: true}));
            if (window.jQuery) window.jQuery(select).trigger('change');
            """,
            select_element,
            option_value,
        )
        time.sleep(0.3)  # Fast reactive debounce for AJAX dispatch

    # 9. Sequential Dropdown Hierarchy
    update_status("navigating", f"Selecting {TARGET_DISTRICT} > {TARGET_TALUK} > {TARGET_VILLAGE} > Survey {TARGET_SURVEY_NO}/{TARGET_SUB_DIV}...")
    select_option('//*[@id="district-dropdown"]', TARGET_DISTRICT)
    select_option('//*[@id="taluk-dropdown"]', TARGET_TALUK)
    select_option('//*[@id="village-dropdown"]', TARGET_VILLAGE)
    select_option('//*[@id="survey-number-dropdown"]', TARGET_SURVEY_NO)
    select_option('//*[@id="sub-division-dropdown"]', TARGET_SUB_DIV)

    print("Workflow navigation complete.")
    time.sleep(1.0)  # Brief pause for map canvas to center

    import base64
    map_b64 = None
    map_elem = None
    map_png_path = f"tngis_map_{SESSION_ID}.png" if SESSION_ID else None
    try:
        for sel in [
            '//*[@id="map"]',
            '//div[contains(@class, "ol-viewport")]',
            '//canvas',
            '//*[@id="map-container"]',
        ]:
            try:
                elems = driver.find_elements(By.XPATH, sel)
                if elems and elems[0].is_displayed():
                    map_elem = elems[0]
                    break
            except Exception:
                continue

        if map_elem:
            screenshot_bytes = map_elem.screenshot_as_png
        else:
            screenshot_bytes = driver.get_screenshot_as_png()

        if screenshot_bytes:
            map_b64 = f"data:image/png;base64,{base64.b64encode(screenshot_bytes).decode('utf-8')}"
            if map_png_path:
                with open(map_png_path, "wb") as mf:
                    mf.write(screenshot_bytes)
    except Exception as map_err:
        print(f"[TNGIS] Map screenshot capture notice: {map_err}")

    update_status(
        "waiting_for_pin",
        f"Map centered for Survey {TARGET_SURVEY_NO}/{TARGET_SUB_DIV}. Click on the parcel in the preview map to pin it.",
        {
            "district": TARGET_DISTRICT,
            "taluk": TARGET_TALUK,
            "village": TARGET_VILLAGE,
            "survey": TARGET_SURVEY_NO,
            "subdiv": TARGET_SUB_DIV,
            "map_image": map_b64,
        },
    )

    if SIGNAL_FILE:
        print(f"[TNGIS] Waiting for map pin confirmation (watching {SIGNAL_FILE})...")
        start_wait = time.time()
        x_ratio = 0.5
        y_ratio = 0.5
        while time.time() - start_wait < 300:  # 5 minutes timeout
            if os.path.exists(SIGNAL_FILE):
                print("[TNGIS] Continue signal received! Processing parcel pin click...")
                try:
                    with open(SIGNAL_FILE, "r", encoding="utf-8") as sf:
                        raw_sig = sf.read().strip()
                        if raw_sig.startswith("{"):
                            sig_data = json.loads(raw_sig)
                            x_ratio = float(sig_data.get("x_ratio", 0.5))
                            y_ratio = float(sig_data.get("y_ratio", 0.5))
                except Exception:
                    pass
                try:
                    os.remove(SIGNAL_FILE)
                except Exception:
                    pass
                break
            time.sleep(1)
        else:
            print("[TNGIS] Pin wait timeout reached. Proceeding with center coordinates...")

        # Emulate click on map canvas at specified ratios
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            target_map = map_elem
            if not target_map:
                for sel in ['//*[@id="map"]', '//div[contains(@class, "ol-viewport")]', '//canvas']:
                    try:
                        elems = driver.find_elements(By.XPATH, sel)
                        if elems and elems[0].is_displayed():
                            target_map = elems[0]
                            break
                    except Exception:
                        continue
            if target_map:
                size = target_map.size
                offset_x = int((x_ratio - 0.5) * size['width'])
                offset_y = int((y_ratio - 0.5) * size['height'])
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(target_map, offset_x, offset_y).click().perform()
                print(f"[TNGIS] Emulated parcel click on map canvas: ratio=({x_ratio:.2f}, {y_ratio:.2f}), offset=({offset_x}, {offset_y})")
                time.sleep(0.8)
        except Exception as click_err:
            print(f"[TNGIS] Map canvas click emulation notice: {click_err}")

    elif not NON_INTERACTIVE:
        input("Pin the point on the map, then press Enter here to continue: ")
    else:
        print("Non-interactive mode active: proceeding with automated panel extraction...")
        time.sleep(0.5)

    update_status("extracting", "Extracting Owner Information, Land Details, Patta, Guideline Value, and GPS Vertices...")

    results_filename = OUTPUT_FILE
    with open(results_filename, "w", encoding="utf-8") as results_file:
        save_result_section(
            results_file,
            "Search",
            f"District: {TARGET_DISTRICT}\n"
            f"Taluk: {TARGET_TALUK}\n"
            f"Village: {TARGET_VILLAGE}\n"
            f"Survey number: {TARGET_SURVEY_NO}\n"
            f"Subdivision: {TARGET_SUB_DIV}\n",
        )

        # Optional owner and land panels must not block the remaining workflow.
        if click_if_present(driver, '//*[@id="profile-tab"]/img', timeout=3):
            wait_for_panel_loading(driver, timeout=3)
            save_result_section(
                results_file,
                "Owner information",
                extract_panel_data(driver, '//*[@id="areg-tab-container"]/div', timeout=5),
            )
        else:
            save_result_section(results_file, "Owner information", "Owner tab unavailable.")

        if click_if_present(driver, '//*[@id="land-tab"]', timeout=3):
            wait_for_panel_loading(driver, timeout=3)
            save_result_section(
                results_file,
                "Land information",
                extract_panel_data(driver, '//*[@id="areg-tab-container"]/div', timeout=5),
            )
        else:
            save_result_section(results_file, "Land information", "Land tab unavailable.")

        # Start with Patta.
        patta_available = click_if_present(driver, '//*[@id="patta-download-tab"]', timeout=3)
        if patta_available:
            wait_for_panel_loading(driver, timeout=3)
            patta_text = extract_panel_data(
                driver,
                '//*[@id="areg-tab-container"]/div',
                timeout=4,
            )
            fullscreen_available = click_if_present(driver, '//*[@id="fullscreenPattaBtn"]', timeout=2)
            if fullscreen_available:
                time.sleep(0.3)
            patta_status = (
                patta_text or "[Patta panel contained no text data]"
            ) + f"\nFullscreen opened: {fullscreen_available}\n"
            save_result_section(results_file, "Patta view", patta_status)
        else:
            save_result_section(results_file, "Patta view", "Patta tab unavailable; continuing.")

        fmb_available = click_if_present(driver, '//*[@id="next-tab"]/img', timeout=3)
        if fmb_available:
            wait_for_panel_loading(driver, timeout=3)
            fmb_sketch_available = click_if_present(
                driver,
                '//*[@id="fmb-sketch-info-panel"]/div/button[1]',
                timeout=2,
            )
            if fmb_sketch_available:
                wait_for_panel_loading(driver, timeout=3)
            fmb_text = extract_panel_data(
                driver,
                '//*[@id="areg-tab-container"]/div',
                timeout=4,
            )
            save_result_section(
                results_file,
                "FMB information",
                (fmb_text or "FMB panel opened, but it contained no text data.")
                + f"\nSketch button: {fmb_sketch_available}"
            )
        else:
            save_result_section(results_file, "FMB information", "FMB tab unavailable; continuing.")

        property_available = click_if_present(driver, '//*[@id="pro-tab"]/img', timeout=3)
        if property_available:
            wait_for_panel_loading(driver, timeout=3)
            # Explicitly extract the vertex table from //*[@id="vertex-info-container"]/div[2]/table
            vertex_table_xpath = '//*[@id="vertex-info-container"]/div[2]/table'
            vertex_text = ""
            try:
                table_el = WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((By.XPATH, vertex_table_xpath))
                )
                # Extract clean rows from table cells
                table_text = driver.execute_script("""
                    const table = arguments[0];
                    if (!table) return '';
                    const rows = Array.from(table.querySelectorAll('tr'));
                    return rows.map(r => {
                        const cells = Array.from(r.querySelectorAll('th, td')).map(c => (c.innerText || c.textContent || '').trim());
                        return cells.join(' ');
                    }).filter(line => line.length > 0).join('\\n');
                """, table_el)
                vertex_text = (table_text or "").strip()
            except Exception:
                pass

            if not vertex_text:
                vertex_text = extract_dom_text_if_present(
                    driver,
                    vertex_table_xpath,
                    timeout=3,
                ) or extract_text_if_present(
                    driver,
                    vertex_table_xpath,
                    timeout=3,
                ) or extract_text_if_present(
                    driver,
                    '//*[@id="vertex-info-container"]',
                    timeout=3,
                )

            actual_coordinates = extract_text_if_present(
                driver,
                '//*[@id="staticBackdropLabel"]/span',
                timeout=3,
            )
            property_data = (
                vertex_text or "[No vertex table data extracted]"
            ) + (
                "\n\nActual pinned latitude/longitude:\n"
                + (actual_coordinates or "[Coordinates unavailable]")
            )
            save_result_section(results_file, "Property vertices", property_data)
        else:
            save_result_section(
                results_file,
                "Property vertices",
                "Property tab unavailable; continuing to guideline value.",
            )

        guideline_available = click_first_available(
            driver,
            [
                '//*[@id="igr-info-container"]',
                '//*[@id="guideline-tab"]',
                "//*[normalize-space()='G-Value']/ancestor::*[@role='button' or self::a or self::button][1]",
                "//*[normalize-space()='G-Value']",
                '//*[contains(translate(@id, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "guideline")]//*[self::img or self::button][1]',
                '//*[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "guideline")][self::a or self::button or self::label][1]',
            ],
            timeout=2,
        ) or element_exists(driver, '//*[@id="igr-info-container"]', timeout=2)
        if guideline_available:
            wait_for_panel_loading(driver, timeout=3)
            guideline_panel_text = extract_text_if_present(
                driver,
                '//*[@id="igr-info-container"]',
                timeout=3,
            )
            guideline_block_text = extract_text_if_present(
                driver,
                '//*[@id="igr-info-container"]/div[2]/div[3]',
                timeout=3,
            )
            if not guideline_block_text:
                guideline_block_text = extract_dom_text_if_present(
                    driver,
                    '//*[@id="igr-info-container"]/div[2]/div[3]',
                )
            guideline_amount = extract_text_if_present(
                driver,
                '//*[@id="igr-info-container"]/div[2]/div[3]/div[2]',
            )
            if not guideline_amount:
                guideline_amount = extract_dom_text_if_present(
                    driver,
                    '//*[@id="igr-info-container"]/div[2]/div[3]/div[2]',
                )
            if not guideline_panel_text:
                guideline_panel_text = extract_panel_data(
                    driver,
                    '//*[@id="igr-info-container"]',
                    container_xpath='//*[@id="offcanvasScrolling-right"]',
                    timeout=10,
                )
            guideline_text = guideline_panel_text or "Guideline control opened, but no text data was available."
            guideline_text += "\nSpecific guideline block:\n"
            guideline_text += guideline_block_text or "[block unavailable]"
            guideline_text += "\nGuideline amount:\n"
            guideline_text += guideline_amount or "[amount unavailable]"
            save_result_section(
                results_file,
                "Guideline value",
                guideline_text,
            )
        else:
            save_result_section(results_file, "Guideline value", "Guideline value unavailable; continuing.")

        ec_available = click_first_available(
            driver,
            [
                '//*[@id="EC_logo"]',
                '//*[contains(translate(@id, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "ec")][self::img or self::button or self::a][1]',
            ],
            timeout=3,
        )
        if ec_available:
            wait_for_panel_loading(driver, timeout=30)
            save_result_section(
                results_file,
                "EC",
                "EC panel opened.",
            )
        else:
            save_result_section(results_file, "EC", "EC unavailable.")

        if not any((patta_available, fmb_available, guideline_available, ec_available)):
            if not NON_INTERACTIVE:
                input("No Patta, FMB, guideline, or EC panel was available. Inspect the browser, then press Enter: ")

    print(f"Map details saved to '{results_filename}'.")
    update_status("completed", "TNGIS extraction completed successfully.", {
        "output_file": os.path.abspath(results_filename),
    })

except Exception as err:
    print(f"[TNGIS Error] {err}")
    update_status("error", str(err))
    raise

finally:
    if NON_INTERACTIVE or IS_HEADLESS or SESSION_ID:
        try:
            driver.quit()
        except Exception:
            pass