"""
Standalone TNREGINET Encumbrance Certificate (EC) Scraper
==========================================================
Run directly from your terminal to see the live Chrome browser window:
    python tnec_scraper/scraping.py

Or with custom parameters:
    python tnec_scraper/scraping.py --survey 370 --start-date 01/01/1975
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)


def to_tn_portal_date(dt_str: str) -> str:
    """
    Converts DD/MM/YYYY, DD-MM-YYYY, or YYYY-MM-DD to portal's required DD-Mon-YYYY (e.g. 01-Jan-1975).
    """
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


def prompt_captcha_modal(image_path: str) -> str:
    """Displays a graphical desktop modal dialog with the CAPTCHA image and input box."""
    try:
        import tkinter as tk
        from PIL import Image as PilImg, ImageTk

        solved_val = [""]

        root = tk.Tk()
        root.title("TNREGINET Security CAPTCHA")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        root.configure(bg="#0f172a")

        # Center on screen
        w, h = 460, 310
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        root.geometry(f"{w}x{h}+{x}+{y}")

        lbl_title = tk.Label(
            root,
            text="🔐 TNREGINET CAPTCHA Verification",
            font=("Segoe UI", 13, "bold"),
            bg="#0f172a",
            fg="#f8fafc",
        )
        lbl_title.pack(pady=(16, 4))

        lbl_sub = tk.Label(
            root,
            text="Type the 5 characters from the image below and press Enter:",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8",
        )
        lbl_sub.pack(pady=(0, 10))

        # Show image
        if os.path.exists(image_path):
            img_raw = PilImg.open(image_path)
            img_scaled = img_raw.resize((img_raw.width * 2 + 30, img_raw.height * 2 + 10), PilImg.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img_scaled)
            img_lbl = tk.Label(root, image=tk_img, bg="#ffffff", bd=3, relief="solid")
            img_lbl.image = tk_img
            img_lbl.pack(pady=(0, 12))

        entry_var = tk.StringVar()
        entry = tk.Entry(
            root,
            textvariable=entry_var,
            font=("Consolas", 18, "bold"),
            justify="center",
            width=12,
            bd=2,
            relief="solid",
            bg="#1e293b",
            fg="#38bdf8",
            insertbackground="#38bdf8"
        )
        entry.pack(pady=(0, 14))
        entry.focus_force()

        def to_upper(*args):
            v = entry_var.get()
            if v != v.upper():
                entry_var.set(v.upper())

        entry_var.trace_add("write", to_upper)

        def on_submit(event=None):
            val = entry_var.get().strip().upper()
            if val:
                solved_val[0] = val
                root.destroy()

        btn = tk.Button(
            root,
            text="Confirm & Search ➔",
            command=on_submit,
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            padx=18,
            pady=6,
            relief="flat",
            cursor="hand2",
        )
        btn.pack()

        root.bind("<Return>", on_submit)
        root.lift()
        root.focus_force()
        root.mainloop()

        return solved_val[0]
    except Exception as e:
        print(f"      [!] Desktop modal unavailable ({e}), falling back to terminal entry.")
        return ""


def run_standalone_scrape(
    zone_id: str = "15",
    district_id: str = "20005",
    sro_id: str = "20111:1",
    village_id: str = "700604229",
    survey_no: str = "370",
    sub_division_no: str = "",
    start_date: str = "01/01/1975",
    end_date: str = None,
    download_dir: str = "downloads",
    headless: bool = True
):
    start_date_tn = to_tn_portal_date(start_date)
    end_date_tn = (
        to_tn_portal_date(end_date)
        if end_date
        else (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
    )

    abs_download_dir = os.path.abspath(download_dir)
    os.makedirs(abs_download_dir, exist_ok=True)

    mode_label = "HIDDEN BACKGROUND" if headless else "VISIBLE CHROME"
    print("=" * 65)
    print(f"      TNREGINET STANDALONE EC SCRAPER ({mode_label})")
    print("=" * 65)
    print(f"Zone ID:        {zone_id} (Chengalpattu)")
    print(f"District ID:    {district_id} (Kancheepuram)")
    print(f"SRO ID:         {sro_id} (Walajabad)")
    print(f"Village ID:     {village_id} (UTHUKKADU -B)")
    print(f"Survey Number:  {survey_no}/{sub_division_no}")
    print(f"Search Period:  {start_date_tn}  to  {end_date_tn}")
    print(f"Download Path:  {abs_download_dir}")
    print("=" * 65)

    # Configure Chrome options
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
    else:
        opts.add_experimental_option("detach", True)
        opts.add_argument("--start-maximized")

    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    prefs = {
        "download.default_directory": abs_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True
    }
    opts.add_experimental_option("prefs", prefs)

    launch_msg = "Launching hidden background Chrome browser..." if headless else "Launching visible Chrome browser window on your desktop..."
    print(f"\n[1/6] {launch_msg}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    wait = WebDriverWait(driver, 20)

    if headless:
        try:
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": abs_download_dir
            })
        except Exception:
            pass

    try:
        # 1. Open Portal
        print("[2/6] Loading TNREGINET Portal...")
        driver.get("https://tnreginet.gov.in/portal/")
        time.sleep(2)
        driver.execute_script("""
            document.querySelectorAll('.modal, .modal-backdrop').forEach(e => e.remove());
            document.body.classList.remove('modal-open');
        """)

        # 2. Navigate to EC Search
        print("[3/6] Navigating to Encumbrance Certificate Search...")
        driver.execute_script("menuAct('webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true');")
        time.sleep(2.5)

        # 3. Fill Dropdowns
        print(f"      - Selecting Zone: {zone_id}...")
        Select(wait.until(EC.presence_of_element_located((By.ID, "cmb_Zone")))).select_by_value(str(zone_id))
        time.sleep(1)

        print(f"      - Selecting District: {district_id}...")
        Select(wait.until(EC.presence_of_element_located((By.ID, "cmb_District")))).select_by_value(str(district_id))
        time.sleep(1)

        print(f"      - Selecting SRO: {sro_id}...")
        Select(wait.until(EC.presence_of_element_located((By.ID, "cmb_SroName")))).select_by_value(str(sro_id))
        time.sleep(1)

        print(f"      - Selecting Village: {village_id}...")
        Select(wait.until(EC.presence_of_element_located((By.ID, "cmb_Village")))).select_by_value(str(village_id))
        time.sleep(0.5)

        # 4. Inject Dates
        print(f"[4/6] Setting search date range: {start_date_tn} to {end_date_tn}...")
        driver.execute_script("""
            $('#txt_PeriodStartDt').val(arguments[0]);
            $('#txt_PeriodEndDt').val(arguments[1]);
            document.querySelectorAll('.datepick-popup').forEach(e => e.remove());
        """, start_date_tn, end_date_tn)
        time.sleep(0.5)

        # 5. Add Survey
        print(f"      - Adding Survey {survey_no}/{sub_division_no} to search table...")
        survey_box = driver.find_element(By.ID, "txt_SurveyNo")
        survey_box.clear()
        survey_box.send_keys(survey_no)
        if sub_division_no:
            sub_box = driver.find_element(By.ID, "txt_SubDivisionNo")
            sub_box.clear()
            sub_box.send_keys(sub_division_no)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btn_AddSurvey"))
        time.sleep(1)

        # 6. CAPTCHA entry via Modal
        print("[5/6] Waiting for manual CAPTCHA entry in modal dialog...")
        cdiv = wait.until(EC.presence_of_element_located((By.ID, "cmnCaptchDivId")))
        c_img = cdiv.find_element(By.TAG_NAME, "img")
        cap_file = os.path.join(abs_download_dir, "current_captcha.png")
        c_img.screenshot(cap_file)

        # Launch Desktop GUI Modal
        solved = prompt_captcha_modal(cap_file)
        if not solved:
            solved = input("      Enter CAPTCHA from the Chrome tab: ").strip().upper()

        print(f"      - Entering CAPTCHA: '{solved}'...")
        cbox = driver.find_element(By.ID, "txt_Captcha")
        cbox.clear()
        cbox.send_keys(solved)
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """, cbox)
        time.sleep(0.5)

        # 7. Submit Search
        print("[6/6] Submitting Search to TNREGINET...")
        search_btn = driver.find_element(By.ID, "btn_SearchDoc")
        driver.execute_script("arguments[0].click();", search_btn)

        # The portal shows a generated Smoke.js alert before rendering either result state.
        alert_root = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, "//*[starts-with(@id, 'smoke-out-')]"))
        )
        alert_message = alert_root.find_elements(By.XPATH, "./div[2]/div")
        if alert_message:
            print(f"      - Portal alert: {alert_message[0].text.strip()}")

        ok_alert = WebDriverWait(driver, 10).until(
            lambda d: next(
                (
                    element for element in d.find_elements(By.CSS_SELECTOR, "[id^='alert-ok-']")
                    if element.is_displayed()
                ),
                False,
            )
        )
        print("      - Confirming portal alert...")
        try:
            ok_alert.click()
        except Exception:
            driver.execute_script("arguments[0].click();", ok_alert)
        WebDriverWait(driver, 10).until(
            lambda d: not any(
                element.is_displayed()
                for element in d.find_elements(By.XPATH, "//*[starts-with(@id, 'smoke-out-')]")
            )
        )

        success_xpath = "//*[@id='successPage']/div[2]/div/div[2]/h2[2]/a/span"
        
        def check_portal_status(d):
            return d.execute_script("""
                // 1. Success Page Check (Explicit link, successPage div, or table rows)
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

                // 2. Visible Nil Check (MUST BE VISIBLE, not display: none)
                var nothingDiv = document.getElementById("divNothingFound");
                if (nothingDiv && nothingDiv.offsetParent !== null && window.getComputedStyle(nothingDiv).display !== 'none') {
                    return 'nil';
                }

                // Check failure message inside divPropertyList (only if visible!)
                var innerDiv = document.querySelector("#divPropertyList > div");
                if (innerDiv && innerDiv.offsetParent !== null && window.getComputedStyle(innerDiv).display !== 'none') {
                    var txt = innerDiv.innerText.trim().toLowerCase();
                    if (txt.includes("no document") || txt.includes("no record") || txt.includes("எந்த ஆவணங்களும்") || txt.includes("பதிவு செய்யப்படவில்லை")) {
                        return 'nil';
                    }
                }

                return false;
            """, success_xpath)

        result_state = WebDriverWait(driver, 30).until(check_portal_status)
        print(f"      - Portal result state: {result_state}")

        print("\n" + "=" * 65)
        print("                 SEARCH RESULTS SUMMARY")
        print("=" * 65)

        if result_state == "success":
            print("STATUS: ENCUMBRANCE RECORDS FOUND!")
            
            # 1. Click download button on success page
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
                print("Download button clicked successfully.")

            # 2. Highlight download button with glowing smart square
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
            print("Smart Square highlight added to download button in the Chrome window.")

            # 3. Monitor download folder for EC statement PDF
            print(f"Waiting for EC PDF to download to: {abs_download_dir}...")
            downloaded_pdf = None
            start_wait = time.time()
            while time.time() - start_wait < 30:
                pdfs = [f for f in os.listdir(abs_download_dir) if f.lower().endswith(".pdf") and not f.lower().endswith(".crdownload")]
                if pdfs:
                    pdfs.sort(key=lambda x: os.path.getmtime(os.path.join(abs_download_dir, x)), reverse=True)
                    downloaded_pdf = os.path.join(abs_download_dir, pdfs[0])
                    break
                time.sleep(1)

            if downloaded_pdf and os.path.exists(downloaded_pdf):
                print(f"\n[DOWNLOAD COMPLETE] Saved EC PDF to:\n  -> {downloaded_pdf} ({os.path.getsize(downloaded_pdf)} bytes)")
            else:
                print("Download initiated. You can view or save the EC statement directly from the visible Chrome tab.")

        elif result_state == "nil":
            nil_msg = driver.execute_script("""
                var nd = document.getElementById("divNothingFound");
                if (nd && nd.offsetParent !== null) return nd.innerText.trim();
                var fd = document.querySelector("#divPropertyList > div");
                if (fd && fd.offsetParent !== null) return fd.innerText.trim();
                return "No registered documents found during search period.";
            """)
            print("STATUS: VERIFIED NIL ENCUMBRANCE (FORM 16)")
            print(f"PORTAL MESSAGE: {nil_msg}")
            print("\nResult: No registered documents found for this survey in the search period.")
            print("This parcel has a clean title back to 01-Jan-1975.")
        else:
            print("STATUS: NO ENCUMBRANCE RECORDS FOUND")

        print("=" * 65)
        if not headless:
            print("\nSUCCESS: The Chrome tab will remain OPEN on your desktop.")
            print("You can inspect elements, verify records, or close the tab whenever you are ready.\n")
        else:
            print("\nSUCCESS: EC Search completed in hidden mode.")
            print(f"Check '{abs_download_dir}' for your downloaded files.\n")
            try:
                driver.quit()
            except Exception:
                pass

    except Exception as e:
        print(f"\n[ERROR] Scraping encountered an error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone TNREGINET Scraper")
    parser.add_argument("--zone", default="15", help="Zone ID (default: 15 for Chengalpattu)")
    parser.add_argument("--district", default="20005", help="District ID (default: 20005 for Kancheepuram)")
    parser.add_argument("--sro", default="20111:1", help="SRO ID (default: 20111:1 for Walajabad)")
    parser.add_argument("--village", default="700604229", help="Village ID (default: 700604229 for UTHUKKADU -B)")
    parser.add_argument("--survey", default="370", help="Survey Number (default: 370)")
    parser.add_argument("--subdivision", default="4", help="Subdivision Number (default: 4 for Uthukaadu parcel)")
    parser.add_argument("--start-date", default="01/01/1975", help="Start Date (DD/MM/YYYY, default: 01/01/1975)")
    parser.add_argument("--end-date", default="", help="End Date (DD/MM/YYYY, defaults to current date)")
    parser.add_argument("--download-dir", default="downloads", help="Directory to save downloaded PDFs")
    parser.add_argument("--headed", action="store_true", help="Launch visible Chrome browser window on desktop")
    parser.add_argument("--headless", action="store_true", default=True, help="Run Chrome in hidden background mode (default: True)")
    args = parser.parse_args()

    run_standalone_scrape(
        zone_id=args.zone,
        district_id=args.district,
        sro_id=args.sro,
        village_id=args.village,
        survey_no=args.survey,
        sub_division_no=args.subdivision,
        start_date=args.start_date,
        end_date=args.end_date,
        download_dir=args.download_dir,
        headless=not args.headed
    )
