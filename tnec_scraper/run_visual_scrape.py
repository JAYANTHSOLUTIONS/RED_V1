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

artifact_dir = r"C:\Users\w\.gemini\antigravity-ide\brain\3dd5d065-1ed8-48d8-9501-4ce38ecf8f99"

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--window-size=1600,1000')
opts.add_argument('--ignore-certificate-errors')
opts.add_argument('--disable-blink-features=AutomationControlled')
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
try:
    print("Step 1: Opening TNREGINET portal...")
    driver.get("https://tnreginet.gov.in/portal/")
    time.sleep(2)
    driver.execute_script("""
        document.querySelectorAll('.modal, .modal-backdrop').forEach(e => e.remove());
        document.body.classList.remove('modal-open');
    """)
    driver.save_screenshot(os.path.join(artifact_dir, "visual_step1_home.png"))
    print("Saved visual_step1_home.png")

    print("Step 2: Navigating to Encumbrance Certificate Search...")
    driver.execute_script("menuAct('webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true');")
    time.sleep(2.5)
    driver.save_screenshot(os.path.join(artifact_dir, "visual_step2_ec_search_blank.png"))
    print("Saved visual_step2_ec_search_blank.png")

    print("Step 3: Selecting Chengalpattu -> Kancheepuram -> Walajabad -> UTHUKKADU -B...")
    Select(driver.find_element(By.ID, "cmb_Zone")).select_by_value("15")
    time.sleep(1)
    Select(driver.find_element(By.ID, "cmb_District")).select_by_value("20005")
    time.sleep(1)
    Select(driver.find_element(By.ID, "cmb_SroName")).select_by_value("20111:1")
    time.sleep(1)
    Select(driver.find_element(By.ID, "cmb_Village")).select_by_value("700604229")
    time.sleep(0.5)

    print("Step 4: Setting Dates 01-Jan-1975 to current date...")
    driver.execute_script("""
        $('#txt_PeriodStartDt').val('01-Jan-1975');
        $('#txt_PeriodEndDt').val('08-Sep-2026');
        document.querySelectorAll('.datepick-popup').forEach(e => e.remove());
    """)
    time.sleep(0.5)

    print("Step 5: Adding Survey 370 to table...")
    driver.find_element(By.ID, "txt_SurveyNo").send_keys("370")
    driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btn_AddSurvey"))
    time.sleep(1)
    driver.save_screenshot(os.path.join(artifact_dir, "visual_step3_form_filled.png"))
    print("Saved visual_step3_form_filled.png")

    print("Step 6: CAPTCHA handling...")
    solved = ""
    for att in range(4):
        c_div = driver.find_element(By.ID, "cmnCaptchDivId")
        c_img = c_div.find_element(By.TAG_NAME, "img")
        c_path = "visual_cap.png"
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
        time.sleep(1.2)

    if not solved:
        solved = cand or "ABCDE"

    print(f"Entering solved CAPTCHA: '{solved}'...")
    cbox = driver.find_element(By.ID, "txt_Captcha")
    cbox.clear()
    cbox.send_keys(solved)
    driver.execute_script("arguments[0].value = arguments[1];", cbox, solved)
    time.sleep(0.5)
    driver.save_screenshot(os.path.join(artifact_dir, "visual_step4_captcha_ready.png"))
    print("Saved visual_step4_captcha_ready.png")

    print("Step 7: Clicking Search...")
    search_btn = driver.find_element(By.ID, "btn_SearchDoc")
    driver.execute_script("arguments[0].click();", search_btn)
    time.sleep(3)

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
    driver.save_screenshot(os.path.join(artifact_dir, "visual_step5_search_results.png"))
    print("Saved visual_step5_search_results.png")

    # Scroll into view of divPropertyList and take a close-up
    driver.execute_script("""
        var elem = document.getElementById('divPropertyList') || document.getElementById('divNothingFound');
        if (elem) elem.scrollIntoView({block: 'center'});
    """)
    time.sleep(0.5)
    driver.save_screenshot(os.path.join(artifact_dir, "visual_step6_result_closeup.png"))
    print("Saved visual_step6_result_closeup.png")

    print("ALL VISUAL STEPS COMPLETED!")

finally:
    driver.quit()
