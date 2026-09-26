"""
TNREGINET Administrative Hierarchy Harvester
Extracts all Zones, Districts, SROs (Sub-Registrar Offices), and Villages from TNREGINET.
Saves the structured mapping into tnec_hierarchy.json.
"""

import sys
import os
import time
import json
import re
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tnec_hierarchy.json")
BACKEND_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app", "data"))
BACKEND_OUTPUT_FILE = os.path.join(BACKEND_DATA_DIR, "tnec_hierarchy.json")


def parse_select_options(xml_str: str) -> List[Dict[str, str]]:
    """Parses <option value='id'>Name</option> elements from XML response."""
    if not xml_str:
        return []
    matches = re.findall(r"<option\s+value=['\"]([^'\"]+)['\"][^>]*>([^<]+)</option>", xml_str, re.IGNORECASE)
    items = []
    for val, name in matches:
        val = val.strip()
        name = name.strip()
        if val in ["-1", "", "null"] or name in ["- Select -", "தெரிவு செய்க", "--Select--"]:
            continue
        items.append({"id": val, "name": name})
    return items


def harvest_hierarchy(max_zones: int = None, max_sros_per_district: int = None):
    """
    Connects to TNREGINET, initializes session in English, and extracts the full hierarchy.
    """
    print("=" * 60)
    print("Starting TNREGINET Master Hierarchy Harvester")
    print("=" * 60)

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

    try:
        print("1. Opening TNREGINET portal...")
        driver.get("https://tnreginet.gov.in/portal/")
        time.sleep(2)

        # Close mobile modal
        try:
            modal = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="MobileAppModal"]/div/div[1]/span')))
            modal.click()
            print("   - Mobile modal dismissed.")
            time.sleep(0.5)
        except Exception:
            pass

        # Language toggle to English
        try:
            font_elem = driver.find_element(By.XPATH, '//*[@id="fontSelection"]')
            if "English" in font_elem.text:
                font_elem.click()
                print("   - Switched portal locale to English.")
                time.sleep(1.5)
        except Exception:
            pass

        # Open EC Search page
        print("2. Opening Encumbrance Certificate search page...")
        driver.execute_script('menuAct("webHP?requestType=ApplicationRH&actionVal=openEncumbranceCertSearch&screenId=8400001&scenarioId=2&auditUSFlag=true");showProgressbar();')
        time.sleep(2.5)

        driver.set_script_timeout(45)

        # Step 1: Read all Zones from cmb_Zone
        zone_elem = wait.until(EC.presence_of_element_located((By.ID, "cmb_Zone")))
        select_zone = Select(zone_elem)
        zones_raw = [
            {"id": opt.get_attribute("value").strip(), "name": opt.text.strip()}
            for opt in select_zone.options
            if opt.get_attribute("value") not in ["-1", ""] and opt.text.strip() not in ["- Select -", "தெரிவு செய்க"]
        ]
        print(f"   - Discovered {len(zones_raw)} Registration Zones.")

        if max_zones:
            zones_raw = zones_raw[:max_zones]

        # Structure to collect
        hierarchy: Dict[str, Any] = {
            "version": "1.0",
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "zones": []
        }

        # Check existing output to resume if partially done
        existing_data = {}
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                pass

        zone_dict_map = {z["id"]: z for z in existing_data.get("zones", [])}

        total_villages_count = 0
        total_sros_count = 0

        for z_idx, z in enumerate(zones_raw, 1):
            zone_id = z["id"]
            zone_name = z["name"]
            print(f"\n[{z_idx}/{len(zones_raw)}] Zone: {zone_name} (ID: {zone_id})")

            # Check if zone already completely cached with districts & sros
            if zone_id in zone_dict_map and len(zone_dict_map[zone_id].get("districts", [])) > 0:
                districts = zone_dict_map[zone_id]["districts"]
                # Count villages in cached
                cached_vils = sum(len(s.get("villages", [])) for d in districts for s in d.get("sros", []))
                if cached_vils > 0:
                    print(f"   -> Reusing cached data: {len(districts)} districts, {cached_vils} villages.")
                    hierarchy["zones"].append(zone_dict_map[zone_id])
                    total_villages_count += cached_vils
                    continue

            # Fetch districts via internal AJAX endpoint
            dist_res = driver.execute_async_script("""
                const done = arguments[arguments.length - 1];
                const token = getAjaxSecurityToken();
                const url = urlHome + "?requestType=ApplicationRH&actionVal=loadDistrictCombo&queryType=Select&screenId=8400001&comboValue=" + arguments[0] + "&_csrf=" + token;
                fetch(url, { method: 'POST' })
                    .then(r => r.text())
                    .then(data => done({ success: true, data: data }))
                    .catch(err => done({ success: false, error: err.toString() }));
            """, zone_id)

            if not dist_res.get("success"):
                print(f"   [!] Error fetching districts for zone {zone_name}: {dist_res.get('error')}")
                continue

            districts_raw = parse_select_options(dist_res.get("data", ""))
            print(f"   -> Found {len(districts_raw)} Registration Districts.")

            zone_entry = {
                "id": zone_id,
                "name": zone_name,
                "districts": []
            }

            for d in districts_raw:
                dist_id = d["id"]
                dist_name = d["name"]
                print(f"      - District: {dist_name} (ID: {dist_id})")

                # Fetch SROs for this district
                sro_res = driver.execute_async_script("""
                    const done = arguments[arguments.length - 1];
                    const token = getAjaxSecurityToken();
                    const url = urlHome + "?requestType=ApplicationRH&actionVal=loadSroCombo&queryType=Select&screenId=8400001&comboValue=" + arguments[0] + "&_csrf=" + token;
                    fetch(url, { method: 'POST' })
                        .then(r => r.text())
                        .then(data => done({ success: true, data: data }))
                        .catch(err => done({ success: false, error: err.toString() }));
                """, dist_id)

                if not sro_res.get("success"):
                    print(f"         [!] Error fetching SROs: {sro_res.get('error')}")
                    continue

                sros_raw = parse_select_options(sro_res.get("data", ""))
                print(f"         -> Found {len(sros_raw)} Sub-Registrar Offices (SROs).")

                if max_sros_per_district:
                    sros_raw = sros_raw[:max_sros_per_district]

                dist_entry = {
                    "id": dist_id,
                    "name": dist_name,
                    "sros": []
                }

                for s in sros_raw:
                    sro_id = s["id"]
                    sro_name = s["name"]

                    # Fetch Villages for this SRO
                    vil_res = driver.execute_async_script("""
                        const done = arguments[arguments.length - 1];
                        const token = getAjaxSecurityToken();
                        const url = urlHome + "?requestType=ApplicationRH&actionVal=loadVillageCombo&queryType=Select&screenId=8400001&comboValue=" + encodeURIComponent(arguments[0]) + "&_csrf=" + token;
                        fetch(url, { method: 'POST' })
                            .then(r => r.text())
                            .then(data => done({ success: true, data: data }))
                            .catch(err => done({ success: false, error: err.toString() }));
                    """, sro_id)

                    villages_raw = []
                    if vil_res.get("success"):
                        villages_raw = parse_select_options(vil_res.get("data", ""))

                    total_villages_count += len(villages_raw)
                    total_sros_count += 1

                    dist_entry["sros"].append({
                        "id": sro_id,
                        "name": sro_name,
                        "villages": villages_raw
                    })

                zone_entry["districts"].append(dist_entry)

            hierarchy["zones"].append(zone_entry)

            # Save incrementally after each zone
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(hierarchy, f, ensure_ascii=False, indent=2)

        # Write to backend directory as well
        os.makedirs(BACKEND_DATA_DIR, exist_ok=True)
        with open(BACKEND_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(hierarchy, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print("Harvest Completed Successfully!")
        print(f"Total Zones: {len(hierarchy['zones'])}")
        print(f"Total SROs: {total_sros_count}")
        print(f"Total Villages: {total_villages_count}")
        print(f"Saved to: {OUTPUT_FILE}")
        print(f"Saved to: {BACKEND_OUTPUT_FILE}")
        print("=" * 60)
        return hierarchy

    finally:
        driver.quit()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Harvest TNREGINET Administrative Hierarchy")
    parser.add_argument("--max-zones", type=int, default=None, help="Limit number of zones to harvest")
    parser.add_argument("--max-sros", type=int, default=None, help="Limit SROs per district")
    args = parser.parse_args()

    harvest_hierarchy(max_zones=args.max_zones, max_sros_per_district=args.max_sros)
