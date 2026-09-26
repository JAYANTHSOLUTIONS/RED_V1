import os
import sys
import time
from datetime import datetime
from PIL import Image
import pytesseract
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
# DETACH: Tells ChromeDriver not to kill the browser process when the script finishes!
# This ensures Chrome stays open on the user's taskbar and screen.
opts.add_experimental_option("detach", True)
opts.add_argument("--start-maximized")
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

print("Launching visible Chrome window on desktop...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

try:
    print("1. Loading TNREGINET portal...")
    driver.get("https://tnreginet.gov.in/portal/")
    time.sleep(2)
    driver.execute_script("""
        document.querySelectorAll('.modal, .modal-backdrop').forEach(e => e.remove());
        document.body.classList.remove('modal-open');
    """)

    print("2. Opening Encumbrance Certificate Search...")
    driver.execute_script("menuAct('webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true');")
    time.sleep(2.5)

    print("3. Selecting Zone 15 (Chengalpattu)...")
    Select(driver.find_element(By.ID, "cmb_Zone")).select_by_value("15")
    time.sleep(1)

    print("4. Selecting District 20005 (Kancheepuram)...")
    Select(driver.find_element(By.ID, "cmb_District")).select_by_value("20005")
    time.sleep(1)

    print("5. Selecting SRO 20111:1 (Walajabad)...")
    Select(driver.find_element(By.ID, "cmb_SroName")).select_by_value("20111:1")
    time.sleep(1)

    print("6. Selecting Village 700604229 (UTHUKKADU -B)...")
    Select(driver.find_element(By.ID, "cmb_Village")).select_by_value("700604229")
    time.sleep(0.5)

    print("7. Setting Dates from 01-Jan-1975 to current date...")
    driver.execute_script("""
        $('#txt_PeriodStartDt').val('01-Jan-1975');
        $('#txt_PeriodEndDt').val('08-Sep-2026');
        document.querySelectorAll('.datepick-popup').forEach(e => e.remove());
    """)
    time.sleep(0.5)

    print("8. Adding Survey 370...")
    driver.find_element(By.ID, "txt_SurveyNo").send_keys("370")
    driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btn_AddSurvey"))
    time.sleep(1)

    print("9. Solving security CAPTCHA...")
    solved = ""
    for att in range(5):
        c_div = driver.find_element(By.ID, "cmnCaptchDivId")
        c_img = c_div.find_element(By.TAG_NAME, "img")
        c_path = "live_desktop_cap.png"
        c_img.screenshot(c_path)

        img = Image.open(c_path).convert("L")
        img = img.resize((img.width * 3, img.height * 3), Image.Resampling.LANCZOS)
        table = [0 if i < 110 else 255 for i in range(256)]
        img_bin = img.point(table, '1')
        custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(img_bin, config=custom_config).strip()
        cand = "".join([c for c in text if c.isalnum()]).upper()
        if len(cand) == 5:
            solved = cand
            break
        driver.execute_script("doImageReload();")
        time.sleep(1.5)

    if not solved:
        solved = cand or "ABCDE"

    print(f"Entering CAPTCHA '{solved}'...")
    cbox = driver.find_element(By.ID, "txt_Captcha")
    cbox.clear()
    cbox.send_keys(solved)
    driver.execute_script("arguments[0].value = arguments[1];", cbox, solved)
    time.sleep(0.5)

    print("10. Submitting Search...")
    search_btn = driver.find_element(By.ID, "btn_SearchDoc")
    driver.execute_script("arguments[0].click();", search_btn)
    time.sleep(3.5)

    # Dismiss Smoke.js popup
    driver.execute_script("""
        document.querySelectorAll('.smoke-base, .dialog, #alert-ok, .dialog-buttons button').forEach(e => {
            if (e.id === 'alert-ok' || (e.innerText && (e.innerText.includes('சரி') || e.innerText.includes('OK')))) {
                e.click();
            } else {
                e.remove();
            }
        });
    """)
    time.sleep(2)

    # Scroll results into view
    driver.execute_script("""
        var elem = document.getElementById('divPropertyList') || document.getElementById('divNothingFound');
        if (elem) elem.scrollIntoView({behavior: 'smooth', block: 'center'});
    """)

    print("DONE! Chrome window is now detached and will remain permanently open on your taskbar.")
except Exception as e:
    print(f"Error during interactive run: {e}")
# NOTE: Notice driver.quit() is NOT called so the browser remains open on screen!
