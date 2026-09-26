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
        $('#txt_PeriodStartDt').val('01-Jan-1975');
        $('#txt_PeriodEndDt').val('08-Sep-2026');
        var vFrom = validateFromDate();
        var vTo = validateToDate();
        return {
            vFrom: vFrom,
            vTo: vTo,
            startVal: $('#txt_PeriodStartDt').val(),
            endVal: $('#txt_PeriodEndDt').val(),
            errText: $('#incRegDateTo').text()
        };
    """)
    print("Test date format result:", res)
finally:
    driver.quit()
