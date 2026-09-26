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

    # Let's inspect how datepick is initialized
    result = driver.execute_script("""
        var s = $('#txt_PeriodStartDt');
        var e = $('#txt_PeriodEndDt');
        // Let's set values using both jQuery and plain JS
        s.val('01/01/1975');
        e.val('08/09/2026');
        return {
            s_val: s.val(),
            e_val: e.val(),
            hasDatepick: typeof $.fn.datepick !== 'undefined'
        };
    """)
    print("Result after $.val():", result)

    # Now let's see what happens if we trigger validate or checkMandatory
    res2 = driver.execute_script("""
        if (typeof checkPeriodDtMandatory === 'function') {
            return checkPeriodDtMandatory();
        }
        return 'no checkPeriodDtMandatory';
    """)
    print("checkPeriodDtMandatory:", res2)

    # Let's see what validation error appears if any
    res3 = driver.execute_script("""
        return {
            s_val: $('#txt_PeriodStartDt').val(),
            e_val: $('#txt_PeriodEndDt').val(),
            errText: $('.error, .err, .red, span[id*="Dt"]').text()
        };
    """)
    print("After validation:", res3)
finally:
    driver.quit()
