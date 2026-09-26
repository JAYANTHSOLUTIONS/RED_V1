"""
TNREGINET Encumbrance Certificate (EC) Automated Scraper
Operates headlessly in the background:
1. Opens TNREGINET portal, dismisses modal, selects English locale.
2. Navigates to Search / View EC page.
3. Selects Zone -> District -> SRO -> Village.
4. Sets Start Date & End Date.
5. Adds 1 or more Survey Numbers & Subdivisions via btn_AddSurvey.
6. Extracts security CAPTCHA, solves via OCR or interactive modal bridge.
7. Submits search, confirms dialogs, and downloads the official EC PDF.
8. Reports real-time status and milestones into job status file.
"""

import sys
import os
import time
import json
import base64
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

try:
    from PIL import Image, ImageOps, ImageFilter
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None


RUN_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(RUN_DIR, "downloads")


def update_status(job_id: str, status: str, step: int, message: str, **kwargs):
    """Updates status JSON file for backend polling."""
    status_path = os.path.join(RUN_DIR, f"tnec_job_{job_id}.json")
    data = {
        "job_id": job_id,
        "status": status,
        "current_step": step,
        "message": message,
        "timestamp": time.time(),
        **kwargs
    }
    temp_path = status_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, status_path)


def solve_captcha_ocr(image_path: str) -> str:
    """Attempts automated OCR on the TNREGINET CAPTCHA image."""
    if not (Image and pytesseract):
        return ""
    try:
        img = Image.open(image_path).convert("L")
        # Upscale
        img = img.resize((img.width * 3, img.height * 3), Image.Resampling.LANCZOS)
        # Threshold: background is yellow, letters are dark blue/red
        table = []
        for i in range(256):
            # darker pixels become black, lighter pixels become white
            table.append(0 if i < 110 else 255)
        img_bin = img.point(table, '1')
        
        custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(img_bin, config=custom_config).strip()
        # Clean up any spaces
        text = "".join([c for c in text if c.isalnum()]).upper()
        print(f"   [OCR] Candidate text: '{text}' (Length: {len(text)})")
        if len(text) == 5:
            return text
        return ""
    except Exception as e:
        print(f"   [OCR] Exception: {e}")
        return ""


def dismiss_all_modals(driver):
    """Forcefully purges MobileAppModal and any stray backdrop overlays from DOM."""
    try:
        driver.execute_script("""
            const m = document.getElementById('MobileAppModal');
            if (m) {
                m.classList.remove('show');
                m.style.display = 'none';
                m.remove();
            }
            document.querySelectorAll('.modal-backdrop, .modal, .modal-dialog').forEach(el => {
                el.style.display = 'none';
                el.remove();
            });
            document.body.classList.remove('modal-open');
        """)
    except Exception:
        pass


def safe_click(driver, elem):
    """Safely scrolls to element, purges modals, and triggers click via JS."""
    dismiss_all_modals(driver)
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        time.sleep(0.1)
        driver.execute_script("arguments[0].click();", elem)
    except Exception:
        elem.click()


def to_tn_portal_date(dt_str: str) -> str:
    """Converts any date format (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY) to portal's required DD-Mon-YYYY (e.g. 01-Jan-1975)."""
    if not dt_str or not dt_str.strip():
        return "01-Jan-1975"
    dt_str = dt_str.strip()
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for m in months:
        if f"-{m}-" in dt_str:
            return dt_str
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            d = datetime.strptime(dt_str, fmt)
            return d.strftime('%d-%b-%Y')
        except ValueError:
            pass
    return dt_str


def run_tnec_scraper(
    job_id: str,
    zone_id: str,
    district_id: str,
    sro_id: str,
    village_id: str,
    start_date: str = "01/01/1975",
    end_date: str = None,
    surveys: List[Dict[str, str]] = None,
    auto_solve: bool = True,
    headless: bool = True
):
    if not start_date or not start_date.strip():
        start_date = "01/01/1975"

    job_download_dir = os.path.join(DOWNLOADS_DIR, job_id)
    os.makedirs(job_download_dir, exist_ok=True)

    update_status(job_id, "running", 1, "Initializing browser engine & portal session...")

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
    else:
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--window-size=1600,1000")
        chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    prefs = {
        "download.default_directory": job_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # Enable downloads via CDP in headless mode
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": job_download_dir
        })

        print("1. Opening TNREGINET portal...")
        driver.get("https://tnreginet.gov.in/portal/")
        time.sleep(1.5)

        # 1. Close mobile app modal
        dismiss_all_modals(driver)
        try:
            modal = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="MobileAppModal"]/div/div[1]/span')))
            modal.click()
            time.sleep(0.5)
        except Exception:
            pass
        dismiss_all_modals(driver)

        # 2. Change language to English
        try:
            font_elem = driver.find_element(By.XPATH, '//*[@id="fontSelection"]')
            if "English" in font_elem.text:
                font_elem.click()
                time.sleep(1.5)
        except Exception:
            pass

        dismiss_all_modals(driver)
        update_status(job_id, "running", 2, "Navigating to Encumbrance Certificate portal & setting location...")

        # 3. Open Search / View EC page
        driver.execute_script('menuAct("webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true");showProgressbar();')
        time.sleep(2)
        dismiss_all_modals(driver)

        # 4. Select Zone
        zone_elem = wait.until(EC.presence_of_element_located((By.ID, "cmb_Zone")))
        Select(zone_elem).select_by_value(str(zone_id))
        time.sleep(1)
        dismiss_all_modals(driver)

        # 5. Select District
        dist_elem = wait.until(EC.presence_of_element_located((By.ID, "cmb_District")))
        # Wait for options to populate
        wait.until(lambda d: len(Select(d.find_element(By.ID, "cmb_District")).options) > 1)
        Select(dist_elem).select_by_value(str(district_id))
        time.sleep(1)
        dismiss_all_modals(driver)

        # 6. Select SRO
        sro_elem = wait.until(EC.presence_of_element_located((By.ID, "cmb_SroName")))
        wait.until(lambda d: len(Select(d.find_element(By.ID, "cmb_SroName")).options) > 1)
        Select(sro_elem).select_by_value(str(sro_id))
        time.sleep(1)
        dismiss_all_modals(driver)

        # 7. Select Village
        vil_elem = wait.until(EC.presence_of_element_located((By.ID, "cmb_Village")))
        wait.until(lambda d: len(Select(d.find_element(By.ID, "cmb_Village")).options) > 1)
        Select(vil_elem).select_by_value(str(village_id))
        time.sleep(0.5)
        dismiss_all_modals(driver)

        # 8. Set Date range (defaulting to 01-Jan-1975 for TN computerization base)
        start_date_tn = to_tn_portal_date(start_date or "01/01/1975")
        end_date_tn = (
            to_tn_portal_date(end_date)
            if (end_date and end_date.strip())
            else (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        )

        print(f"   - Setting EC search period: {start_date_tn} to {end_date_tn}")
        driver.execute_script("""
            $('#txt_PeriodStartDt').val(arguments[0]);
            $('#txt_PeriodEndDt').val(arguments[1]);
            document.querySelectorAll('.datepick-popup').forEach(e => e.remove());
        """, start_date_tn, end_date_tn)
        time.sleep(0.5)

        # 9. Multi-survey addition
        update_status(job_id, "running", 2, f"Adding {len(surveys)} survey number(s) to search table...")
        survey_input = driver.find_element(By.ID, "txt_SurveyNo")
        subdiv_input = driver.find_element(By.ID, "txt_SubDivisionNo")
        add_btn = driver.find_element(By.ID, "btn_AddSurvey")

        for idx, s in enumerate(surveys, 1):
            s_no = str(s.get("survey_no", "")).strip()
            s_sub = str(s.get("sub_division_no", "")).strip()

            survey_input.clear()
            survey_input.send_keys(s_no)

            subdiv_input.clear()
            if s_sub:
                subdiv_input.send_keys(s_sub)

            # Purge any overlays and click safely via JavaScript
            safe_click(driver, add_btn)
            time.sleep(0.6)
            print(f"   - Added Survey {s_no}/{s_sub} to table.")

        # 10. Security CAPTCHA handling (with auto-retry & seamless interactive fallback)
        max_attempts = 4
        attempt = 0
        search_succeeded = False

        while attempt < max_attempts:
            attempt += 1
            update_status(job_id, "running", 3, f"Processing security CAPTCHA (attempt {attempt}/{max_attempts})...")
            captcha_div = wait.until(EC.presence_of_element_located((By.ID, "cmnCaptchDivId")))
            time.sleep(0.5)
            captcha_img = captcha_div.find_element(By.TAG_NAME, "img")

            # Save captcha screenshot
            captcha_path = os.path.join(job_download_dir, f"captcha_attempt_{attempt}.png")
            captcha_img.screenshot(captcha_path)

            with open(captcha_path, "rb") as f:
                captcha_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

            solved_text = ""
            # On attempt 1, attempt OCR if auto_solve is enabled (try up to 3 reloads for clean image)
            if attempt == 1 and auto_solve:
                for reload_i in range(3):
                    solved_text = solve_captcha_ocr(captcha_path)
                    if len(solved_text) == 5:
                        print(f"   - OCR successfully resolved 5-char token: '{solved_text}' (try {reload_i+1})")
                        break
                    print(f"   - OCR candidate '{solved_text}' not 5 chars, trying image reload...")
                    driver.execute_script("""
                        try {
                            if (typeof doImageReload === 'function') doImageReload();
                            else { var ref = document.getElementById('refresh'); if (ref) ref.click(); }
                        } catch(e) {}
                    """)
                    time.sleep(1.2)
                    captcha_div = wait.until(EC.presence_of_element_located((By.ID, "cmnCaptchDivId")))
                    captcha_img = captcha_div.find_element(By.TAG_NAME, "img")
                    captcha_img.screenshot(captcha_path)
                    with open(captcha_path, "rb") as f:
                        captcha_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

            # If OCR failed or this is a retry attempt after rejection:
            if not solved_text or len(solved_text) != 5:
                prompt_msg = (
                    "Please enter the 5-character security CAPTCHA shown above to continue."
                    if attempt == 1 else
                    f"Previous CAPTCHA was rejected or expired. Please enter the fresh 5-character code shown above (Attempt {attempt}/{max_attempts}):"
                )
                update_status(
                    job_id,
                    "waiting_for_captcha",
                    3,
                    prompt_msg,
                    captcha_image=captcha_b64,
                    surveys_count=len(surveys)
                )

                # Wait for signal file from backend API
                signal_file = os.path.join(RUN_DIR, f"tnec_signal_{job_id}.json")
                timeout = 180  # 3 minutes for human verification
                start_wait = time.time()
                while time.time() - start_wait < timeout:
                    if os.path.exists(signal_file):
                        try:
                            with open(signal_file, "r", encoding="utf-8") as sf:
                                sig_data = json.load(sf)
                            solved_text = sig_data.get("captcha_text", "").strip()
                            os.remove(signal_file)
                            if solved_text:
                                print(f"   - Received manual CAPTCHA input: {solved_text}")
                                break
                        except Exception:
                            pass
                    time.sleep(1)

            if not solved_text:
                raise RuntimeError("CAPTCHA input timed out or was not provided.")

            # 11. Enter CAPTCHA & click Search
            update_status(job_id, "running", 4, f"Submitting EC search with security CAPTCHA ({solved_text})...")
            dismiss_all_modals(driver)

            # Find txt_Captcha input box
            captcha_box = None
            for cid in ["txt_Captcha", "captcha_text", "txtCaptcha"]:
                c_elems = driver.find_elements(By.ID, cid)
                if c_elems and c_elems[0].tag_name.lower() == "input":
                    captcha_box = c_elems[0]
                    break

            if not captcha_box:
                cand_inputs = driver.find_elements(By.XPATH, "//input[contains(@id, 'Captcha') or contains(@name, 'Captcha')]")
                for ci in cand_inputs:
                    if ci.get_attribute("type") == "text":
                        captcha_box = ci
                        break

            if captcha_box:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", captcha_box)
                try:
                    captcha_box.clear()
                    captcha_box.send_keys(solved_text)
                except Exception:
                    pass
                driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                """, captcha_box, solved_text)
                print(f"   - Successfully typed and triggered CAPTCHA '{solved_text}' into txt_Captcha.")

            time.sleep(0.5)

            search_btn = driver.find_element(By.ID, "btn_SearchDoc")
            safe_click(driver, search_btn)
            time.sleep(2.5)

            # Check for alerts / popup confirmations
            has_captcha_error = False
            # Dismiss Smoke.js dialogs and alerts using exact portal selectors
            try:
                alert_root = WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.XPATH, "//*[starts-with(@id, 'smoke-out-')]"))
                )
                alert_message = alert_root.find_elements(By.XPATH, "./div[2]/div")
                if alert_message:
                    print(f"   - Portal alert: {alert_message[0].text.strip()}")

                ok_alert = WebDriverWait(driver, 5).until(
                    lambda d: next(
                        (
                            element for element in d.find_elements(By.CSS_SELECTOR, "[id^='alert-ok-']")
                            if element.is_displayed()
                        ),
                        False,
                    )
                )
                print("   - Confirming portal alert...")
                try:
                    ok_alert.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", ok_alert)
                WebDriverWait(driver, 5).until(
                    lambda d: not any(
                        element.is_displayed()
                        for element in d.find_elements(By.XPATH, "//*[starts-with(@id, 'smoke-out-')]")
                    )
                )
            except Exception:
                try:
                    driver.execute_script("""
                        document.querySelectorAll('.smoke-base, .dialog, #alert-ok, .dialog-buttons button').forEach(e => {
                            if (e.id === 'alert-ok' || (e.innerText && (e.innerText.includes('சரி') || e.innerText.includes('OK')))) {
                                e.click();
                            } else {
                                e.remove();
                            }
                        });
                    """)
                    time.sleep(0.5)
                except Exception:
                    pass

            try:
                alert = driver.switch_to.alert
                alert_text = alert.text.lower()
                print("   - Native alert text:", alert_text)
                alert.accept()
                time.sleep(0.5)
                if any(k in alert_text for k in ["captcha", "குறியீடு", "verification", "invalid", "valid", "தவறாக"]):
                    has_captcha_error = True
            except Exception:
                pass

            # Poll for portal result state after search submission & alert dismissal
            success_xpath = "//*[@id='successPage']/div[2]/div/div[2]/h2[2]/a/span"

            def get_portal_result(d):
                return d.execute_script("""
                    try {
                        // 1. CAPTCHA error check
                        var incMsg = document.getElementById("incCaptcha") ? document.getElementById("incCaptcha").innerText.trim() : "";
                        if (incMsg) return 'captcha_error';

                        // 2. Success check (Visible successPage, success link, or table rows)
                        var successLink = document.evaluate(
                            arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                        ).singleNodeValue;
                        var sp = document.getElementById("successPage");
                        var isSpVisible = sp && (sp.offsetParent !== null || window.getComputedStyle(sp).display !== 'none');
                        if (successLink || isSpVisible) return 'success';

                        var tableRows = document.querySelectorAll("#divPropertyList table tr");
                        if (tableRows.length > 1) return 'success';

                        var submitBtn = document.getElementById("submitPersonalDetail");
                        if (submitBtn && submitBtn.offsetParent !== null) return 'success';

                        // 3. Visible Nil Check (MUST BE VISIBLE, not display: none)
                        var nothingDiv = document.getElementById("divNothingFound");
                        if (nothingDiv && nothingDiv.offsetParent !== null && window.getComputedStyle(nothingDiv).display !== 'none') {
                            return 'nil';
                        }

                        var innerDiv = document.querySelector("#divPropertyList > div");
                        if (innerDiv && innerDiv.offsetParent !== null && window.getComputedStyle(innerDiv).display !== 'none') {
                            var inTxt = innerDiv.innerText.trim().toLowerCase();
                            if (inTxt.includes("no document") || inTxt.includes("no record") || inTxt.includes("எந்த ஆவணங்களும்") || inTxt.includes("பதிவு செய்யப்படவில்லை")) {
                                return 'nil';
                            }
                        }

                        return false;
                    } catch(e) {
                        return false;
                    }
                """, success_xpath)

            result_state = False
            try:
                result_state = WebDriverWait(driver, 20).until(get_portal_result)
            except Exception:
                pass
            print(f"   - Portal result state: {result_state}")

            if result_state == "captcha_error" or has_captcha_error:
                print(f"   [!] CAPTCHA '{solved_text}' was rejected by TNREGINET. Reloading fresh CAPTCHA...")
                driver.execute_script("""
                    try {
                        if (typeof doImageReload === 'function') {
                            doImageReload();
                        } else {
                            var ref = document.getElementById('refresh');
                            if (ref) ref.click();
                        }
                    } catch(e) {}
                """)
                time.sleep(1.5)
                continue

            elif result_state == "nil":
                nil_text = driver.execute_script("""
                    var nd = document.getElementById("divNothingFound");
                    if (nd && nd.offsetParent !== null) return nd.innerText.trim();
                    var fd = document.querySelector("#divPropertyList > div");
                    if (fd && fd.offsetParent !== null) return fd.innerText.trim();
                    return "No transaction records found for the selected survey parcels.";
                """)
                print(f"   [SUCCESS - NIL RESULT] Confirmed Nil Encumbrance: '{nil_text}'")
                update_status(
                    job_id,
                    "completed",
                    5,
                    f"Search completed: Nil Encumbrance (Form 16) — {nil_text}",
                    is_nil_encumbrance=True,
                    surveys_count=len(surveys)
                )
                return

            elif result_state == "success":
                search_succeeded = True
                print("   [SUCCESS] Encumbrance records found on portal.")
                break
            else:
                print("   [!] Result state pending, proceeding with download attempt...")
                search_succeeded = True
                break

        if not search_succeeded:
            diag_path = os.path.join(job_download_dir, "result_screen.png")
            driver.save_screenshot(diag_path)
            raise RuntimeError("Portal rejected the CAPTCHA after multiple attempts. Please re-run the search with a fresh CAPTCHA code.")

        # 13. Trigger Encumbrance Certificate Statement Download
        update_status(job_id, "running", 5, "Encumbrance records found! Downloading official EC Statement...")
        time.sleep(1)

        download_button = None
        try:
            download_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, success_xpath))
            )
        except Exception:
            try:
                download_button = driver.find_element(By.CSS_SELECTOR, "#successPage h2 a, #successPage a")
            except Exception:
                pass

        if download_button:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
            time.sleep(0.5)
            try:
                download_button.click()
            except Exception:
                driver.execute_script("arguments[0].click();", download_button)
            print("   - Clicked EC statement download button on success page.")

        # 13b. Highlight download button with glowing Smart Square pointer
        try:
            driver.execute_script("""
                var btn = document.querySelector("#successPage a") || document.getElementById('submitPersonalDetail') || document.querySelector("input[onclick*='previewPdf']") || document.querySelector("input[value*='PDF']");
                if (btn) {
                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                    btn.style.outline = '4px solid #10b981';
                    btn.style.boxShadow = '0 0 25px #10b981, 0 0 50px rgba(16, 185, 129, 0.6)';
                    btn.style.borderRadius = '8px';
                    btn.style.transition = 'all 0.3s ease-in-out';
                }
            """)
            smart_sq_path = os.path.join(job_download_dir, "download_button_smart_square.png")
            driver.save_screenshot(smart_sq_path)
            print("   - Highlighted download button with Smart Square pointer:", smart_sq_path)
        except Exception:
            pass


        # 15. Verify and capture downloaded EC PDF
        def is_valid_ec_pdf(f_name: str) -> bool:
            low = f_name.lower()
            return low.endswith(".pdf") and not any(k in low for k in ["help", "driver", "policy", "keyboard"])

        pdf_file = None
        for _ in range(25):
            files = [f for f in os.listdir(job_download_dir) if is_valid_ec_pdf(f)]
            if files:
                pdf_file = os.path.join(job_download_dir, files[0])
                break
            time.sleep(1)

        # Check if PDF downloaded
        if pdf_file and os.path.exists(pdf_file):
            filename = os.path.basename(pdf_file)
            size_bytes = os.path.getsize(pdf_file)
            print(f"   [SUCCESS] EC PDF downloaded: {filename} ({size_bytes} bytes)")

            update_status(
                job_id,
                "completed",
                5,
                f"Encumbrance Certificate (EC) successfully downloaded ({filename}).",
                pdf_filename=filename,
                pdf_path=pdf_file,
                surveys_count=len(surveys)
            )
        else:
            # Check if it was a Nil Encumbrance result (no transactions recorded in period)
            sec_text = driver.execute_script("return document.getElementById('searchComponentSection') ? document.getElementById('searchComponentSection').innerText : document.body.innerText;")
            if any(k in sec_text.lower() for k in ["no record", "no records", "nil", "பதிவு ஏதும் இல்லை"]):
                update_status(
                    job_id,
                    "completed",
                    5,
                    "Search completed: Nil Encumbrance (Form 16) — No transaction records found for the selected survey parcels in this period.",
                    is_nil_encumbrance=True,
                    surveys_count=len(surveys)
                )
            else:
                diag_path = os.path.join(job_download_dir, "result_screen.png")
                driver.save_screenshot(diag_path)
                raise RuntimeError("EC PDF generation did not start. Portal may require re-submitting with a fresh CAPTCHA.")


    except Exception as e:
        print(f"   [ERROR] Scraper failed: {e}")
        update_status(job_id, "failed", 0, f"Scraper error: {str(e)}", error=str(e))
        raise
    finally:
        if not headless:
            print("   - [Headed Mode] Keeping browser window visible on screen for 15 seconds for user inspection...")
            time.sleep(15)
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TNREGINET EC Scraper Engine")
    parser.add_argument("--job-id", required=True, help="Unique job identifier")
    parser.add_argument("--zone-id", required=True, help="Zone code (e.g. 15)")
    parser.add_argument("--district-id", required=True, help="District code (e.g. 20004)")
    parser.add_argument("--sro-id", required=True, help="SRO code (e.g. 20088:1)")
    parser.add_argument("--village-id", required=True, help="Village code (e.g. 961)")
    parser.add_argument("--start-date", default="01/01/1975", help="Start Date (DD/MM/YYYY, default: 01/01/1975)")
    parser.add_argument("--end-date", default="", help="End Date (DD/MM/YYYY)")
    parser.add_argument("--surveys-json", required=True, help="JSON string or file with survey numbers")
    parser.add_argument("--no-auto-solve", action="store_true", help="Disable automated OCR")
    parser.add_argument("--headed", action="store_true", help="Launch visible Chrome browser window on screen")
    parser.add_argument("--show-browser", action="store_true", help="Launch visible Chrome browser window on screen")
    parser.add_argument("--headless", action="store_true", help="Run in hidden background headless mode")
    args = parser.parse_args()

    try:
        if os.path.exists(args.surveys_json):
            with open(args.surveys_json, "r", encoding="utf-8") as f:
                surveys_list = json.load(f)
        else:
            surveys_list = json.loads(args.surveys_json)
    except Exception:
        surveys_list = [{"survey_no": args.surveys_json, "sub_division_no": ""}]

    # Hidden / Headless Chrome is default unless --headed or --show-browser is explicitly passed
    is_headless = True
    if args.headed or args.show_browser or (os.getenv("TNEC_HEADED", "0") == "1"):
        is_headless = False

    run_tnec_scraper(
        job_id=args.job_id,
        zone_id=args.zone_id,
        district_id=args.district_id,
        sro_id=args.sro_id,
        village_id=args.village_id,
        start_date=args.start_date,
        end_date=args.end_date,
        surveys=surveys_list,
        auto_solve=not args.no_auto_solve,
        headless=is_headless
    )
