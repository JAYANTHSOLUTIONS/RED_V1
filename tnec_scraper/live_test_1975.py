import os
import sys
import time
import json
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

def to_tn_portal_date(dt_str: str) -> str:
    dt_str = dt_str.strip()
    # If already DD-Mon-YYYY e.g. 01-Jan-1975
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for m in months:
        if f"-{m}-" in dt_str:
            return dt_str
    
    # Try parsing YYYY-MM-DD or DD/MM/YYYY or DD-MM-YYYY
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            d = datetime.strptime(dt_str, fmt)
            return d.strftime('%d-%b-%Y')
        except ValueError:
            pass
    return dt_str

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--window-size=1920,1080')
opts.add_argument('--ignore-certificate-errors')
opts.add_argument('--disable-blink-features=AutomationControlled')
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
try:
    print("1. Opening portal...")
    driver.get("https://tnreginet.gov.in/portal/")
    time.sleep(2)
    driver.execute_script("""
        document.querySelectorAll('.modal, .modal-backdrop').forEach(e => e.remove());
        document.body.classList.remove('modal-open');
    """)

    print("2. Navigating to EC Search...")
    driver.execute_script("menuAct('webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true');")
    time.sleep(2)

    print("3. Selecting Zone 15...")
    Select(driver.find_element(By.ID, "cmb_Zone")).select_by_value("15")
    time.sleep(1)

    print("4. Selecting District 20005...")
    Select(driver.find_element(By.ID, "cmb_District")).select_by_value("20005")
    time.sleep(1)

    print("5. Selecting SRO 20111:1 (Walajabad)...")
    Select(driver.find_element(By.ID, "cmb_SroName")).select_by_value("20111:1")
    time.sleep(1)

    print("6. Selecting Village 700604229 (UTHUKKADU -B)...")
    Select(driver.find_element(By.ID, "cmb_Village")).select_by_value("700604229")
    time.sleep(0.5)

    start_date_tn = to_tn_portal_date("01/01/1975") # '01-Jan-1975'
    end_date_tn = to_tn_portal_date("08/09/2026")   # '08-Sep-2026'

    print(f"7. Setting Dates: {start_date_tn} to {end_date_tn}...")
    driver.execute_script("""
        $('#txt_PeriodStartDt').val(arguments[0]);
        $('#txt_PeriodEndDt').val(arguments[1]);
        document.querySelectorAll('.datepick-popup').forEach(e => e.remove());
    """, start_date_tn, end_date_tn)
    time.sleep(0.5)

    print("8. Adding Survey 370...")
    driver.find_element(By.ID, "txt_SurveyNo").send_keys("370")
    driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btn_AddSurvey"))
    time.sleep(1)

    # CAPTCHA solving loop (up to 5 refreshes until OCR gets 5 clean chars)
    solved = ""
    for c_att in range(1, 8):
        captcha_div = driver.find_element(By.ID, "cmnCaptchDivId")
        captcha_img = captcha_div.find_element(By.TAG_NAME, "img")
        captcha_path = f"captcha_att_{c_att}.png"
        captcha_img.screenshot(captcha_path)

        # OCR attempt
        img = Image.open(captcha_path).convert("L")
        img = img.resize((img.width * 3, img.height * 3), Image.Resampling.LANCZOS)
        table = [0 if i < 110 else 255 for i in range(256)]
        img_bin = img.point(table, '1')
        custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(img_bin, config=custom_config).strip()
        cand = "".join([c for c in text if c.isalnum()]).upper()
        print(f"   [Attempt {c_att}] OCR candidate: '{cand}'")

        if len(cand) == 5:
            solved = cand
            break

        # Refresh CAPTCHA
        driver.execute_script("doImageReload();")
        time.sleep(1.5)

    if not solved:
        print("Could not auto-solve 5 chars in 7 attempts, using last candidate")
        solved = cand

    print(f"9. Entering CAPTCHA: '{solved}'...")
    cbox = driver.find_element(By.ID, "txt_Captcha")
    cbox.clear()
    cbox.send_keys(solved)
    driver.execute_script("arguments[0].value = arguments[1];", cbox, solved)
    time.sleep(0.5)

    print("10. Submitting Search...")
    search_btn = driver.find_element(By.ID, "btn_SearchDoc")
    driver.execute_script("arguments[0].click();", search_btn)
    time.sleep(4)

    # Dismiss alerts if any
    try:
        alert = driver.switch_to.alert
        print("Alert text:", alert.text)
        alert.accept()
    except Exception:
        pass

    driver.execute_script("""
        document.querySelectorAll('.smoke-base, .dialog, #alert-ok').forEach(e => {
            if (e.id === 'alert-ok' || e.innerText.includes('சரி') || e.innerText.includes('OK')) e.click();
            else e.remove();
        });
    """)

    driver.save_screenshot("search_1975_result.png")

    info = driver.execute_script("""
        return {
            appTransId: document.getElementById('appTransId') ? document.getElementById('appTransId').value : '',
            isECValid: document.getElementById('isECValid') ? document.getElementById('isECValid').value : '',
            divPropText: document.getElementById('divPropertyList') ? document.getElementById('divPropertyList').innerText : '',
            divNothingText: document.getElementById('divNothingFound') ? document.getElementById('divNothingFound').innerText : '',
            countNoRecords: document.getElementById('countNoRecords') ? document.getElementById('countNoRecords').value : '',
            hasDocTable: document.querySelectorAll('#divPropertyList table tr').length > 0,
            hasDownloadBtn: !!document.getElementById('submitPersonalDetail')
        };
    """)

    with open("search_1975_summary.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print("SUCCESS: Summary written to search_1975_summary.json")

finally:
    driver.quit()
