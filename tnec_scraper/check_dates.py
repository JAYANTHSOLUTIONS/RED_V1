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
    start_val = driver.find_element(By.ID, 'txt_PeriodStartDt').get_attribute('value')
    end_val = driver.find_element(By.ID, 'txt_PeriodEndDt').get_attribute('value')
    print("Initial start_val:", repr(start_val))
    print("Initial end_val:", repr(end_val))
    # Check max date or datepicker config
    dp_info = driver.execute_script("""
        return {
            start_val: $('#txt_PeriodStartDt').val(),
            end_val: $('#txt_PeriodEndDt').val(),
            today: new Date().toISOString()
        };
    """)
    print("DP info:", dp_info)
finally:
    driver.quit()
