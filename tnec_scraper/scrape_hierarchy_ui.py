"""
TNREGINET Full Dropdown UI Cascade Scraper
Visits https://tnreginet.gov.in/portal/, navigates to View EC,
and drives the real DOM select elements:
1. Dismisses //*[@id="MobileAppModal"]/div/div[1]/span
2. Toggles language //*[@id="fontSelection"]
3. Selects Zone from //*[@id="cmb_Zone"]
4. Selects District from //*[@id="cmb_District"]
5. Selects SRO from //*[@id="cmb_SroName"]
6. Extracts all villages from //*[@id="cmb_Village"]
7. Saves all corresponding mappings into a JSON file.
"""

import sys
import os
import time
import json
import argparse
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "tnreginet_ui_cascade_mapping.json")


def run_ui_cascade_scraper(limit_zones: int = None, limit_sros: int = None):
    print("=" * 65)
    print("TNREGINET UI Cascading Dropdown Scraper Starting")
    print("=" * 65)

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)

    all_mappings = []
    summary = {
        "source_url": "https://tnreginet.gov.in/portal/",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zones": []
    }

    try:
        print("1. Visiting https://tnreginet.gov.in/portal/ ...")
        driver.get("https://tnreginet.gov.in/portal/")
        time.sleep(2)

        # Step 1: Close mobile app modal
        try:
            modal_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="MobileAppModal"]/div/div[1]/span')))
            modal_btn.click()
            print("   - Dismissed MobileAppModal.")
            time.sleep(0.5)
        except Exception:
            pass

        # Step 2: Language selection
        try:
            font_btn = driver.find_element(By.XPATH, '//*[@id="fontSelection"]')
            if "English" in font_btn.text:
                font_btn.click()
                print("   - Changed language via fontSelection.")
                time.sleep(1.5)
        except Exception:
            pass

        # Step 3: Navigate to View EC
        print("2. Opening View EC search...")
        driver.execute_script('menuAct("webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true");showProgressbar();')
        time.sleep(2.5)

        # Step 4: Extract Zones from cmb_Zone
        zone_select = Select(wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_Zone"]'))))
        zone_options = [
            (opt.get_attribute("value").strip(), opt.text.strip())
            for opt in zone_select.options
            if opt.get_attribute("value") not in ["-1", ""] and opt.text.strip() not in ["- Select -", "தெரிவு செய்க"]
        ]
        print(f"   - Found {len(zone_options)} Zones in //*[@id='cmb_Zone'].")

        if limit_zones:
            zone_options = zone_options[:limit_zones]

        for z_idx, (zone_id, zone_name) in enumerate(zone_options, 1):
            print(f"\n[{z_idx}/{len(zone_options)}] Selecting Zone: {zone_name} (Value: {zone_id})")
            
            # Select Zone
            zone_select = Select(driver.find_element(By.XPATH, '//*[@id="cmb_Zone"]'))
            zone_select.select_by_value(zone_id)
            time.sleep(1)

            # Wait for District dropdown to populate
            dist_elem = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_District"]')))
            wait.until(lambda d: len(Select(d.find_element(By.XPATH, '//*[@id="cmb_District"]')).options) > 1)
            dist_select = Select(dist_elem)

            dist_options = [
                (opt.get_attribute("value").strip(), opt.text.strip())
                for opt in dist_select.options
                if opt.get_attribute("value") not in ["-1", ""] and opt.text.strip() not in ["- Select -", "தெரிவு செய்க"]
            ]
            print(f"   -> Found {len(dist_options)} Districts in //*[@id='cmb_District'].")

            zone_record = {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "districts": []
            }

            for dist_id, dist_name in dist_options:
                print(f"      Selecting District: {dist_name} (Value: {dist_id})")
                dist_select = Select(driver.find_element(By.XPATH, '//*[@id="cmb_District"]'))
                dist_select.select_by_value(dist_id)
                time.sleep(1)

                # Wait for SRO dropdown to populate
                sro_elem = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_SroName"]')))
                wait.until(lambda d: len(Select(d.find_element(By.XPATH, '//*[@id="cmb_SroName"]')).options) > 1)
                sro_select = Select(sro_elem)

                sro_options = [
                    (opt.get_attribute("value").strip(), opt.text.strip())
                    for opt in sro_select.options
                    if opt.get_attribute("value") not in ["-1", ""] and opt.text.strip() not in ["- Select -", "தெரிவு செய்க"]
                ]
                print(f"         -> Found {len(sro_options)} SROs in //*[@id='cmb_SroName'].")

                if limit_sros:
                    sro_options = sro_options[:limit_sros]

                dist_record = {
                    "district_id": dist_id,
                    "district_name": dist_name,
                    "sros": []
                }

                for sro_id, sro_name in sro_options:
                    print(f"            Selecting SRO: {sro_name} (Value: {sro_id})")
                    sro_select = Select(driver.find_element(By.XPATH, '//*[@id="cmb_SroName"]'))
                    sro_select.select_by_value(sro_id)
                    time.sleep(0.8)

                    # Wait for Village dropdown to populate
                    vil_elem = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_Village"]')))
                    # Wait briefly for villages
                    time.sleep(0.5)
                    vil_select = Select(vil_elem)

                    vil_options = [
                        {"village_id": opt.get_attribute("value").strip(), "village_name": opt.text.strip()}
                        for opt in vil_select.options
                        if opt.get_attribute("value") not in ["-1", ""] and opt.text.strip() not in ["- Select -", "தெரிவு செய்க"]
                    ]
                    print(f"               -> Extracted {len(vil_options)} Villages from //*[@id='cmb_Village'].")

                    # Record mapping
                    sro_record = {
                        "sro_id": sro_id,
                        "sro_name": sro_name,
                        "villages": vil_options
                    }
                    dist_record["sros"].append(sro_record)

                    # Add to flat list
                    for v in vil_options:
                        all_mappings.append({
                            "zone_id": zone_id,
                            "zone_name": zone_name,
                            "district_id": dist_id,
                            "district_name": dist_name,
                            "sro_id": sro_id,
                            "sro_name": sro_name,
                            "village_id": v["village_id"],
                            "village_name": v["village_name"]
                        })

                zone_record["districts"].append(dist_record)

            summary["zones"].append(zone_record)

            # Incremental save
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "summary": summary,
                    "total_records": len(all_mappings),
                    "mappings": all_mappings
                }, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 65)
        print("Extraction Completed Successfully!")
        print(f"Total Flat Records Extracted: {len(all_mappings)}")
        print(f"Saved to: {OUTPUT_FILE}")
        print("=" * 65)

    finally:
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TNREGINET UI Cascade Dropdown Scraper")
    parser.add_argument("--limit-zones", type=int, default=None, help="Limit number of zones to process")
    parser.add_argument("--limit-sros", type=int, default=None, help="Limit number of SROs per district")
    args = parser.parse_args()

    run_ui_cascade_scraper(limit_zones=args.limit_zones, limit_sros=args.limit_sros)
