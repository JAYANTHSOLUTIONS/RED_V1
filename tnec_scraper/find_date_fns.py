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

    btn_html = driver.find_element(By.ID, 'btn_SearchDoc').get_attribute('outerHTML')

    res = driver.execute_script("""
        var scripts = Array.from(document.querySelectorAll('script')).map(s => s.innerText).join('\\n');
        return {
            btn_onclick: $('#btn_SearchDoc').attr('onclick') || document.getElementById('btn_SearchDoc').getAttribute('onclick'),
            scripts_len: scripts.length
        };
    """)

    # Extract the search function
    search_fn = driver.execute_script("""
        if (typeof searchDocument === 'function') return searchDocument.toString();
        if (typeof searchDoc === 'function') return searchDoc.toString();
        if (typeof preSearch === 'function') return preSearch.toString();
        if (typeof submitForm === 'function') return submitForm.toString();
        return 'not found';
    """)

    with open("date_fns_out.txt", "w", encoding="utf-8") as f:
        f.write("btn_html: " + btn_html + "\n")
        f.write("res: " + str(res) + "\n")
        f.write("search_fn:\n" + search_fn + "\n")
    print("Done writing date_fns_out.txt")
finally:
    driver.quit()
