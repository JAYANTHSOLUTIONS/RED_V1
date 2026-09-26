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

    res = driver.execute_script("""
        return {
            start_format: $.datepick ? $('#txt_PeriodStartDt').datepick('option', 'dateFormat') : 'no datepick',
            opts: $('#txt_PeriodStartDt').data('datepick') ? $('#txt_PeriodStartDt').data('datepick').options : 'no data'
        };
    """)
    with open("dp_format.txt", "w", encoding="utf-8") as f:
        f.write(str(res))
    print("Saved dp_format.txt")
finally:
    driver.quit()
