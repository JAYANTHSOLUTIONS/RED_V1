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

    driver.execute_script("""
        $('#txt_PeriodStartDt').val('01/01/1975');
        $('#txt_PeriodEndDt').val('08/09/2026');
        try {
            $('#txt_PeriodStartDt').datepick('setDate', '01/01/1975');
            $('#txt_PeriodEndDt').datepick('setDate', '08/09/2026');
        } catch(e) {
            console.log(e);
        }
    """)

    # Check searchDocValidation
    val_res = driver.execute_script("""
        if (typeof searchDocValidation === 'function') {
            return searchDocValidation.toString();
        }
        return 'not found';
    """)
    print("searchDocValidation JS code:")
    print(val_res[:1500])

    # Let's inspect checkPeriodDt
    chk_res = driver.execute_script("""
        if (typeof checkPeriodDt === 'function') {
            return checkPeriodDt.toString();
        }
        return 'no checkPeriodDt';
    """)
    print("checkPeriodDt:", chk_res)

finally:
    driver.quit()
