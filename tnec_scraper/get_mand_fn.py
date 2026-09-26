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

    fn = driver.execute_script("""
        if (typeof checkMandSearchDocYearWise === 'function') return checkMandSearchDocYearWise.toString();
        return 'not found';
    """)

    with open("checkMandSearchDocYearWise.js", "w", encoding="utf-8") as f:
        f.write(fn)
    print("Length:", len(fn))
finally:
    driver.quit()
