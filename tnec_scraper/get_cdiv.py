from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opts = Options()
opts.add_argument('--headless=new')
driver = webdriver.Chrome(options=opts)
try:
    driver.get('https://tnreginet.gov.in/portal/')
    time.sleep(2)
    driver.execute_script("menuAct('webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true');")
    time.sleep(2)

    c_html = driver.find_element(By.ID, 'cmnCaptchDivId').get_attribute('outerHTML')
    with open("captcha_div.html", "w", encoding="utf-8") as f:
        f.write(c_html)
    print("Saved captcha_div.html")
finally:
    driver.quit()
