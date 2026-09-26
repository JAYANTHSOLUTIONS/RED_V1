from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

opts = Options()
opts.add_argument('--headless=new')
driver = webdriver.Chrome(options=opts)
try:
    driver.get('https://tnreginet.gov.in/portal/')
    time.sleep(2)
    driver.execute_script("menuAct('webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true');")
    time.sleep(2)

    fn1 = driver.execute_script("return typeof validateFromDate === 'function' ? validateFromDate.toString() : 'none';")
    fn2 = driver.execute_script("return typeof validateToDate === 'function' ? validateToDate.toString() : 'none';")

    with open("validateDates.js", "w", encoding="utf-8") as f:
        f.write("// validateFromDate\n" + fn1 + "\n\n// validateToDate\n" + fn2)
    print("Length:", len(fn1) + len(fn2))
finally:
    driver.quit()
