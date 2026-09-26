"""
Service layer for TNREGINET Encumbrance Certificate (EC) operations.
Manages hierarchy data, launches headless scraper jobs, handles CAPTCHA signals,
and attaches downloaded EC documents to the Property Documents Vault.
"""

import os
import sys
import json
import uuid
import time
import shutil
import subprocess
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tnec import TnecScrapeRequest, TnecJobStatus, TnecCaptchaSubmit
from app.models.document import Document
from app.models.property import Property

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRAPER_DIR = os.path.join(BASE_DIR, "tnec_scraper")
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "tnec_hierarchy.json")
FALLBACK_DATA_FILE = os.path.join(SCRAPER_DIR, "tnec_hierarchy.json")
STORAGE_DIR = os.path.join(BASE_DIR, "backend", "storage", "documents")


_hierarchy_cache: Optional[Dict[str, Any]] = None


def load_hierarchy_data() -> Dict[str, Any]:
    global _hierarchy_cache
    if _hierarchy_cache is not None:
        return _hierarchy_cache

    for path in [DATA_FILE, FALLBACK_DATA_FILE]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _hierarchy_cache = json.load(f)
                    return _hierarchy_cache
            except Exception:
                pass

    return {"zones": []}


def get_zones() -> List[Dict[str, str]]:
    data = load_hierarchy_data()
    return [{"id": z["id"], "name": z["name"]} for z in data.get("zones", [])]


def get_districts(zone_id: str) -> List[Dict[str, str]]:
    data = load_hierarchy_data()
    for z in data.get("zones", []):
        if str(z["id"]) == str(zone_id):
            return [{"id": d["id"], "name": d["name"]} for d in z.get("districts", [])]
    return []


def get_sros(zone_id: Optional[str], district_id: str) -> List[Dict[str, str]]:
    data = load_hierarchy_data()
    for z in data.get("zones", []):
        if zone_id and str(z["id"]) != str(zone_id):
            continue
        for d in z.get("districts", []):
            if str(d["id"]) == str(district_id):
                return [{"id": s["id"], "name": s["name"]} for s in d.get("sros", [])]
    return []


def get_villages(sro_id: str) -> List[Dict[str, str]]:
    data = load_hierarchy_data()
    for z in data.get("zones", []):
        for d in z.get("districts", []):
            for s in d.get("sros", []):
                if str(s["id"]) == str(sro_id):
                    return [{"id": v["id"], "name": v["name"]} for v in s.get("villages", [])]
    return []


def _normalize_name(s: str) -> str:
    """Helper to normalize Tamil Nadu revenue place names for resilient matching."""
    if not s:
        return ""
    import re
    s = s.lower().replace("-", " ").replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", "", s)
    # collapse double consecutive letters like kk -> k, pp -> p, ee -> e
    s = re.sub(r"(.)\1+", r"\1", s)
    return " ".join(s.split())


def match_property_location(district: str = "", taluk: str = "", village: str = "") -> Optional[Dict[str, Any]]:
    """Automatically maps property district/taluk/village to TNREGINET Zone, District, SRO, and Village with fuzzy normalization."""
    data = load_hierarchy_data()
    d_q = _normalize_name(district)
    t_q = _normalize_name(taluk)
    v_q = _normalize_name(village)

    if not d_q and not v_q and not t_q:
        return None

    # Helper to find sibling alternate villages in the same SRO
    def get_sibling_villages(sro_obj, current_vil_id, v_token):
        alts = []
        for x in sro_obj.get("villages", []):
            if str(x.get("id")) != str(current_vil_id):
                x_norm = _normalize_name(x.get("name", ""))
                # If sibling shares the root name prefix or token
                if v_token and (v_token in x_norm or x_norm.startswith(v_token[:4])):
                    alts.append({"id": x["id"], "name": x["name"]})
        return alts

    v_root = v_q.split()[0] if v_q else ""

    # Phase 1: Search for direct or normalized village match within matching district
    for z in data.get("zones", []):
        for d in z.get("districts", []):
            d_norm = _normalize_name(d.get("name", ""))
            dist_matched = not d_q or (d_q in d_norm or d_norm in d_q)
            if not dist_matched:
                continue

            for s in d.get("sros", []):
                for v in s.get("villages", []):
                    v_name = v.get("name", "")
                    v_norm = _normalize_name(v_name)

                    # 1. Exact normalized match (e.g. "uthukadu b" == "uthukadu b")
                    if v_q and v_norm == v_q:
                        return {
                            "zone_id": z["id"],
                            "zone_name": z["name"],
                            "district_id": d["id"],
                            "district_name": d["name"],
                            "sro_id": s["id"],
                            "sro_name": s["name"],
                            "village_id": v["id"],
                            "village_name": v_name,
                            "match_confidence": "high",
                            "alternate_villages": get_sibling_villages(s, v["id"], v_root),
                        }

    # Phase 2: Search for substring / root token match on village
    for z in data.get("zones", []):
        for d in z.get("districts", []):
            d_norm = _normalize_name(d.get("name", ""))
            dist_matched = not d_q or (d_q in d_norm or d_norm in d_q)
            if not dist_matched:
                continue

            for s in d.get("sros", []):
                for v in s.get("villages", []):
                    v_name = v.get("name", "")
                    v_norm = _normalize_name(v_name)

                    if v_q and (v_q in v_norm or v_norm in v_q or (v_root and len(v_root) >= 4 and v_root in v_norm)):
                        return {
                            "zone_id": z["id"],
                            "zone_name": z["name"],
                            "district_id": d["id"],
                            "district_name": d["name"],
                            "sro_id": s["id"],
                            "sro_name": s["name"],
                            "village_id": v["id"],
                            "village_name": v_name,
                            "match_confidence": "high",
                            "alternate_villages": get_sibling_villages(s, v["id"], v_root),
                        }

    # Phase 3: Match by Taluk as SRO or Village
    for z in data.get("zones", []):
        for d in z.get("districts", []):
            d_norm = _normalize_name(d.get("name", ""))
            dist_matched = not d_q or (d_q in d_norm or d_norm in d_q)
            if not dist_matched:
                continue

            for s in d.get("sros", []):
                s_norm = _normalize_name(s.get("name", ""))
                if t_q and (t_q in s_norm or s_norm in t_q):
                    # Found matching SRO! Check if any village matches or fallback to first
                    vil_choice = s.get("villages", [{}])[0] if s.get("villages") else {}
                    return {
                        "zone_id": z["id"],
                        "zone_name": z["name"],
                        "district_id": d["id"],
                        "district_name": d["name"],
                        "sro_id": s["id"],
                        "sro_name": s["name"],
                        "village_id": vil_choice.get("id", ""),
                        "village_name": vil_choice.get("name", ""),
                        "match_confidence": "medium",
                        "alternate_villages": [],
                    }

    # Phase 4: Fallback to District level match
    if d_q:
        for z in data.get("zones", []):
            for d in z.get("districts", []):
                d_norm = _normalize_name(d.get("name", ""))
                if d_q in d_norm or d_norm in d_q:
                    if d.get("sros"):
                        first_sro = d["sros"][0]
                        first_vil = first_sro.get("villages", [{}])[0] if first_sro.get("villages") else {}
                        return {
                            "zone_id": z["id"],
                            "zone_name": z["name"],
                            "district_id": d["id"],
                            "district_name": d["name"],
                            "sro_id": first_sro.get("id"),
                            "sro_name": first_sro.get("name"),
                            "village_id": first_vil.get("id", ""),
                            "village_name": first_vil.get("name", ""),
                            "match_confidence": "district_only",
                            "alternate_villages": [],
                        }
    return None



def start_ec_scrape(req: TnecScrapeRequest) -> str:
    """Spawns the background Selenium scraper process for TNEC."""
    job_id = uuid.uuid4().hex[:8]

    # Save initial status
    status_file = os.path.join(SCRAPER_DIR, f"tnec_job_{job_id}.json")
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump({
            "job_id": job_id,
            "property_id": req.property_id,
            "status": "running",
            "current_step": 1,
            "message": "Initializing background Chrome engine...",
            "timestamp": time.time(),
            "surveys_count": len(req.surveys)
        }, f, indent=2)

    # Write surveys to temp json
    surveys_file = os.path.join(SCRAPER_DIR, f"surveys_{job_id}.json")
    with open(surveys_file, "w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in req.surveys], f, indent=2)

    script_path = os.path.join(SCRAPER_DIR, "tnec_scraper.py")
    python_exe = sys.executable

    start_dt = req.start_date.strip() if (req.start_date and req.start_date.strip()) else "01/01/1975"
    end_dt = req.end_date.strip() if (req.end_date and req.end_date.strip()) else time.strftime("%d/%m/%Y")

    cmd = [
        python_exe,
        script_path,
        "--job-id", job_id,
        "--zone-id", str(req.zone_id),
        "--district-id", str(req.district_id),
        "--sro-id", str(req.sro_id),
        "--village-id", str(req.village_id),
        "--start-date", start_dt,
        "--end-date", end_dt,
        "--surveys-json", surveys_file
    ]

    # Run Chrome in hidden headless mode
    cmd.append("--headless")

    # Always require manual CAPTCHA entry in modal for 100% accuracy
    cmd.append("--no-auto-solve")

    subprocess.Popen(
        cmd,
        cwd=SCRAPER_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=(sys.platform != "win32")
    )

    return job_id


async def get_ec_status(job_id: str, session: Optional[AsyncSession] = None) -> TnecJobStatus:
    status_file = os.path.join(SCRAPER_DIR, f"tnec_job_{job_id}.json")
    if not os.path.exists(status_file):
        return TnecJobStatus(
            job_id=job_id,
            status="failed",
            current_step=0,
            message="Job status not found.",
            error="Job not found"
        )

    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return TnecJobStatus(
            job_id=job_id,
            status="running",
            current_step=1,
            message="Reading job status...",
            error=str(e)
        )

    # If completed with PDF and property_id is present, attach to Document Vault
    doc_id = data.get("document_id")
    pdf_path = data.get("pdf_path")
    prop_id = data.get("property_id")

    if data.get("status") == "completed" and pdf_path and os.path.exists(pdf_path) and prop_id and not doc_id and session:
        try:
            filename = os.path.basename(pdf_path)
            os.makedirs(STORAGE_DIR, exist_ok=True)
            storage_filename = f"ec_{job_id}_{filename}"
            storage_path = os.path.join(STORAGE_DIR, storage_filename)
            shutil.copy2(pdf_path, storage_path)

            file_size = os.path.getsize(storage_path)

            doc = Document(
                property_id=prop_id,
                name=f"Encumbrance Certificate ({filename})",
                document_type="EC",
                file_path=storage_path,
                original_filename=filename,
                file_size=file_size,
                mime_type="application/pdf",
                verification_status="VERIFIED",
                notes=f"Automatically downloaded from TNREGINET (Job ID: {job_id})"
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = str(doc.id)

            # Update status file with document_id
            data["document_id"] = doc_id
            data["pdf_url"] = f"/api/v1/documents/{doc_id}/download"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error attaching EC document to DB: {e}")

    return TnecJobStatus(
        job_id=job_id,
        status=data.get("status", "running"),
        current_step=data.get("current_step", 1),
        message=data.get("message", "Processing..."),
        captcha_image=data.get("captcha_image"),
        pdf_filename=data.get("pdf_filename"),
        pdf_url=data.get("pdf_url") or (f"/api/v1/tnec/download/{job_id}" if data.get("pdf_filename") else None),
        document_id=doc_id,
        surveys_count=data.get("surveys_count", 0),
        is_nil_encumbrance=data.get("is_nil_encumbrance", False),
        error=data.get("error")
    )


def submit_captcha_response(submit: TnecCaptchaSubmit) -> bool:
    """Dispatches human solved CAPTCHA to the active scraper."""
    signal_file = os.path.join(SCRAPER_DIR, f"tnec_signal_{submit.job_id}.json")
    with open(signal_file, "w", encoding="utf-8") as f:
        json.dump({"captcha_text": submit.captcha_text.strip().upper()}, f)
    return True


def get_job_pdf_path(job_id: str) -> Optional[str]:
    job_dir = os.path.join(SCRAPER_DIR, "downloads", job_id)
    if os.path.exists(job_dir):
        files = [f for f in os.listdir(job_dir) if f.endswith(".pdf")]
        if files:
            return os.path.join(job_dir, files[0])
    return None
