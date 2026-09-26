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

    fn = driver.execute_script("return typeof getMonthNo === 'function' ? getMonthNo.toString() : 'none';")
    print("getMonthNo:", fn)

    cfd = driver.execute_script("return typeof checkFutureDate === 'function' ? checkFutureDate.toString() : 'none';")
    print("checkFutureDate:", cfd)

    # Also what does the datepicker format default to on these inputs?
    dp_fmt = driver.execute_script("""
        return {
            start_fmt: $('#txt_PeriodStartDt').datepick ? $('#txt_PeriodStartDt').datepick('option', 'dateFormat') : 'no datepick',
            end_fmt: $('#txt_PeriodEndDt').datepick ? $('#txt_PeriodEndDt').datepick('option', 'dateFormat') : 'no datepick'
        };
    """)
    print("DP dateFormat:", dp_fmt)
finally:
    driver.quit()
