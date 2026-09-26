from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import time

opts = Options()
opts.add_argument('--headless=new')
driver = webdriver.Chrome(options=opts)
try:
    driver.get('https://tnreginet.gov.in/portal/')
    time.sleep(2)
    driver.execute_script("menuAct('webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true');")
    time.sleep(2)

    res = driver.execute_script("""
        var btn = document.getElementById('submitPersonalDetail');
        var container = document.getElementById('divViewECPersonalDtl');
        return {
            btnExists: !!btn,
            btnVisible: btn ? ($(btn).is(':visible') && btn.offsetParent !== null) : false,
            btnDisplay: btn ? window.getComputedStyle(btn).display : 'none',
            containerDisplay: container ? window.getComputedStyle(container).display : 'none'
        };
    """)
    with open("btn_info.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("Saved btn_info.json")
finally:
    driver.quit()
