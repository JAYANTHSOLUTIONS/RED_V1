"""
Generates comprehensive mappings for TNREGINET:
1. Nested Hierarchy (Zone -> District -> SRO -> Village)
2. Flat Lookup Records (Zone, District, SRO, Village)
3. Direct ID Mappings for fast querying
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_FILE = os.path.join(BASE_DIR, "tnec_hierarchy.json")
OUT_NESTED = os.path.join(BASE_DIR, "tnreginet_hierarchy_nested.json")
OUT_FLAT = os.path.join(BASE_DIR, "tnreginet_mapping_flat.json")
OUT_SUMMARY = os.path.join(BASE_DIR, "tnreginet_mapping_summary.json")

def process():
    if not os.path.exists(SRC_FILE):
        print(f"Error: {SRC_FILE} not found!")
        return

    with open(SRC_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    zones = data.get("zones", [])
    flat_records = []
    zone_to_districts = {}
    district_to_sros = {}
    sro_to_villages = {}

    total_villages = 0
    total_sros = 0
    total_districts = 0

    for z in zones:
        z_id = z["id"]
        z_name = z["name"]
        zone_to_districts[z_id] = []

        for d in z.get("districts", []):
            d_id = d["id"]
            d_name = d["name"]
            total_districts += 1
            zone_to_districts[z_id].append({"id": d_id, "name": d_name})
            district_to_sros[d_id] = []

            for s in d.get("sros", []):
                s_id = s["id"]
                s_name = s["name"]
                total_sros += 1
                district_to_sros[d_id].append({"id": s_id, "name": s_name})
                sro_to_villages[s_id] = []

                for v in s.get("villages", []):
                    v_id = v["id"]
                    v_name = v["name"]
                    total_villages += 1
                    sro_to_villages[s_id].append({"id": v_id, "name": v_name})

                    flat_records.append({
                        "zone_id": z_id,
                        "zone_name": z_name,
                        "district_id": d_id,
                        "district_name": d_name,
                        "sro_id": s_id,
                        "sro_name": s_name,
                        "village_id": v_id,
                        "village_name": v_name
                    })

    summary = {
        "title": "TNREGINET Administrative Master Mapping (Tamil Nadu)",
        "source": "https://tnreginet.gov.in/portal/",
        "total_zones": len(zones),
        "total_districts": total_districts,
        "total_sros": total_sros,
        "total_villages": total_villages,
        "zones": [
            {
                "id": z["id"],
                "name": z["name"],
                "district_count": len(z.get("districts", [])),
                "sro_count": sum(len(d.get("sros", [])) for d in z.get("districts", [])),
                "village_count": sum(len(s.get("villages", [])) for d in z.get("districts", []) for s in d.get("sros", []))
            }
            for z in zones
        ]
    }

    # Save summary
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Saved summary to {OUT_SUMMARY}")

    # Save flat mapping
    with open(OUT_FLAT, "w", encoding="utf-8") as f:
        json.dump(flat_records, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(flat_records)} flat records to {OUT_FLAT}")

    # Save nested hierarchy
    nested = {
        "summary": summary,
        "zones": zones,
        "zone_to_districts": zone_to_districts,
        "district_to_sros": district_to_sros,
        "sro_to_villages": sro_to_villages
    }
    with open(OUT_NESTED, "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)
    print(f"Saved complete nested mapping to {OUT_NESTED}")

    # Also copy into backend/app/data
    backend_data_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "backend", "app", "data"))
    os.makedirs(backend_data_dir, exist_ok=True)
    with open(os.path.join(backend_data_dir, "tnreginet_mapping_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(os.path.join(backend_data_dir, "tnreginet_hierarchy_nested.json"), "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)
    print("Successfully synced mappings to backend/app/data/")

if __name__ == "__main__":
    process()
