"""Service for parsing and normalizing TNGIS extraction results.

Extracts structured tables (Owners, Land Details, Guideline Valuations,
and Coordinates) from the delimited text output produced by tngis_scraper.
"""
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional

from app.schemas.tngis import (
    TngisCoordinates,
    TngisDocumentStatus,
    TngisGuidelineValue,
    TngisLandDetails,
    TngisLookupResponse,
    TngisOwnerRecord,
    TngisScrapeStatusResponse,
    TngisVertex,
)


def get_default_results_path() -> Path:
    """Locate the default tngis_map_results.txt file in the repository."""
    # Try relative to current backend
    candidates = [
        Path("..") / "tngis_scraper" / "tngis_map_results.txt",
        Path("tngis_scraper") / "tngis_map_results.txt",
        Path(__file__).resolve().parent.parent.parent.parent / "tngis_scraper" / "tngis_map_results.txt",
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    return candidates[0]


def parse_tngis_content(content: str, search_override: Optional[Dict[str, str]] = None) -> TngisLookupResponse:
    """Parse raw delimited text from TNGIS scraper into strongly typed models."""
    sections_raw = re.split(r"={30,}\n(.*?)\n={30,}", content)

    search_dict: Dict[str, str] = {}
    owners: List[TngisOwnerRecord] = []
    land_fields: Dict[str, str] = {}
    guideline_dict: Dict[str, str] = {}
    coordinates: Optional[TngisCoordinates] = None
    doc_status = TngisDocumentStatus()
    raw_sections: Dict[str, str] = {}

    if len(sections_raw) >= 2:
        for i in range(1, len(sections_raw), 2):
            sec_name = sections_raw[i].strip()
            sec_body = sections_raw[i + 1].strip()
            raw_sections[sec_name] = sec_body

            sec_lower = sec_name.lower()

            if sec_lower == "search":
                for line in sec_body.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        search_dict[k.strip().lower().replace(" ", "_")] = v.strip()

            elif sec_lower == "owner information":
                lines = [l.strip() for l in sec_body.splitlines() if l.strip()]
                seen_indices = set()
                for line in lines:
                    parts = re.split(r"\t+|\s{2,}", line)
                    if len(parts) >= 4 and parts[0].isdigit():
                        idx = int(parts[0])
                        if idx not in seen_indices:
                            seen_indices.add(idx)
                            owners.append(
                                TngisOwnerRecord(
                                    index=idx,
                                    owner=parts[1].strip(),
                                    relative=parts[2].strip(),
                                    relation=parts[3].strip(),
                                )
                            )

            elif sec_lower == "land information":
                lines = [l.strip() for l in sec_body.splitlines() if l.strip()]
                for line in lines:
                    if "\t" in line:
                        parts = line.split("\t")
                        k, v = parts[0].strip(), parts[1].strip()
                        if k.lower() != "field":
                            land_fields[k] = v
                    elif "  " in line:
                        parts = re.split(r"\s{2,}", line)
                        if len(parts) >= 2 and parts[0].lower() != "field":
                            land_fields[parts[0].strip()] = parts[1].strip()

            elif sec_lower == "patta view":
                doc_status.patta_available = "patta document" in sec_body.lower()
                pdf_match = re.search(r"rendered pdf:\s*([^\n\r]+)", sec_body, re.IGNORECASE)
                if pdf_match:
                    doc_status.patta_rendered_pdf = pdf_match.group(1).strip()

            elif sec_lower == "fmb information":
                doc_status.fmb_available = "fmb" in sec_body.lower()
                pdf_match = re.search(r"rendered pdf:\s*([^\n\r]+)", sec_body, re.IGNORECASE)
                if pdf_match:
                    doc_status.fmb_rendered_pdf = pdf_match.group(1).strip()
                img_match = re.search(r"screenshot:\s*([^\n\r]+)", sec_body, re.IGNORECASE)
                if img_match:
                    doc_status.fmb_screenshot = img_match.group(1).strip()

            elif sec_lower == "property vertices":
                pinned_lat = None
                pinned_lon = None
                coord_match = re.search(
                    r"Actual pinned latitude/longitude:\s*\n?([0-9.]+),\s*([0-9.]+)",
                    sec_body,
                )
                if coord_match:
                    pinned_lat = float(coord_match.group(1))
                    pinned_lon = float(coord_match.group(2))

                vertices: List[TngisVertex] = []
                v_matches = re.findall(
                    r"^(\d+)\s+([0-9.]+)\s+([0-9.]+)", sec_body, re.MULTILINE
                )
                for vm in v_matches:
                    vertices.append(
                        TngisVertex(
                            vertex_number=int(vm[0]),
                            latitude=float(vm[1]),
                            longitude=float(vm[2]),
                        )
                    )

                if pinned_lat is not None and pinned_lon is not None:
                    coordinates = TngisCoordinates(
                        latitude=pinned_lat,
                        longitude=pinned_lon,
                        google_maps_url=f"https://www.google.com/maps?q={pinned_lat},{pinned_lon}",
                        vertices=vertices,
                    )
                elif vertices:
                    coordinates = TngisCoordinates(
                        latitude=vertices[0].latitude,
                        longitude=vertices[0].longitude,
                        google_maps_url=f"https://www.google.com/maps?q={vertices[0].latitude},{vertices[0].longitude}",
                        vertices=vertices,
                    )

            elif sec_lower == "guideline value":
                lines = [l.strip() for l in sec_body.splitlines() if l.strip()]
                for idx, line in enumerate(lines):
                    if line.lower().startswith("land type:") and idx + 1 < len(lines):
                        guideline_dict["land_type"] = lines[idx + 1].strip()
                    elif line.lower().startswith("metric rate:") and idx + 1 < len(lines):
                        guideline_dict["metric_rate"] = lines[idx + 1].strip()
                    elif line.lower().startswith("guideline amount:") and idx + 1 < len(lines):
                        guideline_dict["guideline_amount"] = lines[idx + 1].strip()

            elif sec_lower == "ec":
                doc_status.ec_available = "ec opened" in sec_body.lower()
                pdf_match = re.search(r"rendered pdf:\s*([^\n\r]+)", sec_body, re.IGNORECASE)
                if pdf_match:
                    doc_status.ec_rendered_pdf = pdf_match.group(1).strip()

    # Apply search overrides if provided by user
    if search_override:
        for k, v in search_override.items():
            if v:
                search_dict[k] = v

    land_details = TngisLandDetails(
        land_type=land_fields.get("Land Type", ""),
        land_type_eng=land_fields.get("Land Type Eng", ""),
        land_type_tamil=land_fields.get("Land Type Tamil", ""),
        govt_pri_code=land_fields.get("Govt Pri Code"),
        soil_class=land_fields.get("Soil Class"),
        soil_type_pri=land_fields.get("Soil Typ Pri"),
        soil_type_sec=land_fields.get("Soil Typ Sec"),
        extent_hectares=land_fields.get("Ext Hect", "0"),
        extent_ares=land_fields.get("Ext Ares", "0"),
        total_tax=land_fields.get("Tot Tax", ""),
        patta_number=land_fields.get("Patta No", ""),
        poramboke=land_fields.get("Poramboke", "-"),
        assessed=land_fields.get("Assessed"),
        cultivable=land_fields.get("Cultivable"),
        raw_fields=land_fields,
    )

    guideline_value = TngisGuidelineValue(
        land_type=guideline_dict.get("land_type", ""),
        metric_rate=guideline_dict.get("metric_rate", ""),
        guideline_amount=guideline_dict.get("guideline_amount", ""),
    )

    return TngisLookupResponse(
        search=search_dict,
        owners=owners,
        land_details=land_details,
        guideline_value=guideline_value,
        coordinates=coordinates,
        document_status=doc_status,
        raw_sections=raw_sections,
        is_cached_sample=True,
        message="TNGIS land and revenue records extracted and structured successfully.",
    )


def is_sample_parcel(search_params: Optional[Dict[str, str]]) -> bool:
    """Check if the search parameters correspond to the Walajabad 217/1B2 sample dataset."""
    if not search_params:
        return True
    d = (search_params.get("district") or "").strip().lower()
    t = (search_params.get("taluk") or "").strip().lower()
    v = (search_params.get("village") or "").strip().lower()
    s = (search_params.get("survey_number") or "").strip().lower()
    sd = (search_params.get("subdivision") or "").strip().lower().replace("-", "").replace(" ", "")

    return (
        d in ("kancheepuram", "kanchipuram")
        and t == "walajabad"
        and v == "walajabad"
        and s == "217"
        and (sd in ("1b2", "1b", "") or not sd)
    )


def get_survey_cache_dir() -> Path:
    """Directory where verified survey parcel records are cached."""
    d = get_scraper_dir() / "survey_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_survey_cache_key(search: Dict[str, str]) -> str:
    """Deterministic cache key based on district, taluk, village, survey, and subdiv."""
    d = (search.get("district") or "").strip().lower()
    t = (search.get("taluk") or "").strip().lower()
    v = (search.get("village") or "").strip().lower()
    s = (search.get("survey_number") or "").strip().lower()
    sd = (search.get("subdivision") or "").strip().lower().replace("/", "_").replace(" ", "")
    return f"{d}_{t}_{v}_{s}_{sd}"


def save_to_survey_cache(data: TngisLookupResponse):
    """Store verified extracted survey record into local survey cache for instant lookups."""
    if not data or not data.search:
        return
    if not data.owners and not data.land_details.patta_number:
        return
    try:
        key = get_survey_cache_key(data.search)
        cache_file = get_survey_cache_dir() / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2))
        print(f"[TNGIS Cache] Cached verified record for {key}")
    except Exception as exc:
        print(f"[TNGIS Cache] Notice saving cache: {exc}")


def load_from_survey_cache(search: Dict[str, str]) -> Optional[TngisLookupResponse]:
    """Retrieve verified survey record from local survey cache in 0.05 seconds."""
    try:
        import json
        key = get_survey_cache_key(search)
        cache_file = get_survey_cache_dir() / f"{key}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cached_resp = TngisLookupResponse(**raw)
            cached_resp.is_cached_sample = is_sample_parcel(search)
            s_num = search.get("survey_number", "")
            s_div = search.get("subdivision", "")
            v_name = search.get("village", "")
            cached_resp.message = f"Instant Cache: Loaded verified TNGIS records for Survey {s_num}{('/' + s_div) if s_div else ''} in {v_name}."
            return cached_resp
    except Exception as exc:
        print(f"[TNGIS Cache] Notice reading cache: {exc}")
    return None


def load_tngis_results(search_params: Optional[Dict[str, str]] = None) -> TngisLookupResponse:
    """Read results. Checks instant survey cache first; returns clean empty if unverified."""
    if search_params:
        cached = load_from_survey_cache(search_params)
        if cached:
            return cached

    if search_params and not is_sample_parcel(search_params):
        s_num = search_params.get("survey_number", "")
        s_div = search_params.get("subdivision", "")
        v_name = search_params.get("village", "")
        t_name = search_params.get("taluk", "")
        return TngisLookupResponse(
            search=search_params,
            owners=[],
            land_details=TngisLandDetails(
                land_type="",
                land_type_eng="",
                land_type_tamil="",
                patta_number="",
                extent_hectares="0",
                extent_ares="0",
                total_tax="",
            ),
            guideline_value=TngisGuidelineValue(
                land_type="",
                metric_rate="",
                guideline_amount="",
            ),
            document_status=TngisDocumentStatus(),
            is_cached_sample=False,
            message=(
                f"No cached records found for Survey {s_num}{('/' + s_div) if s_div else ''} in {v_name}, {t_name}. "
                f"Click 'Fetch & Scrape Details' to fetch live government records in 12s, or toggle 'Edit Mode' below to manually verify and enter owner details."
            ),
        )

    path = get_default_results_path()
    if not path.exists():
        return TngisLookupResponse(
            search=search_params or {},
            owners=[],
            land_details=TngisLandDetails(),
            guideline_value=TngisGuidelineValue(),
            document_status=TngisDocumentStatus(),
            message="No TNGIS results file found.",
        )

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    res = parse_tngis_content(content, search_override=search_params)
    res.is_cached_sample = True
    res.message = "Loaded verified reference sample data for Kancheepuram / Walajabad Survey 217/1B2."
    return res


async def run_live_tngis_scraper(
    district: str,
    taluk: str,
    village: str,
    survey_number: str,
    subdivision: Optional[str] = None,
    area_type: str = "rural",
    timeout_seconds: int = 90,
) -> TngisLookupResponse:
    """Execute tngis_scraper.py asynchronously with user parameters and parse newly extracted output."""
    import asyncio
    import sys
    import uuid

    script_path = (Path(__file__).resolve().parent.parent.parent.parent / "tngis_scraper" / "tngis_scraper.py").resolve()
    if not script_path.exists():
        candidates = [
            Path("..") / "tngis_scraper" / "tngis_scraper.py",
            Path("tngis_scraper") / "tngis_scraper.py",
        ]
        for c in candidates:
            if c.exists():
                script_path = c.resolve()
                break

    output_dir = script_path.parent
    run_id = uuid.uuid4().hex[:8]
    output_file = output_dir / f"tngis_run_{run_id}.txt"

    search_dict = {
        "district": district,
        "taluk": taluk,
        "village": village,
        "survey_number": survey_number,
        "subdivision": subdivision or "",
        "area_type": area_type,
    }

    cmd = [
        sys.executable,
        "-u",
        str(script_path),
        "--district", district,
        "--taluk", taluk,
        "--village", village,
        "--survey", survey_number,
        "--subdiv", subdivision or "",
        "--output", str(output_file),
        "--area-type", area_type,
        "--non-interactive",
        "--headless",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(output_dir),
        )
        await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)

        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()

            res = parse_tngis_content(content, search_override=search_dict)
            if res.owners or res.land_details.patta_number:
                res.is_cached_sample = False
                res.message = f"Live TNGIS scraper successfully extracted revenue records for Survey {survey_number}/{subdivision or ''} in {village}."
                return res
            else:
                return TngisLookupResponse(
                    search=search_dict,
                    owners=[],
                    land_details=TngisLandDetails(),
                    guideline_value=TngisGuidelineValue(),
                    document_status=res.document_status,
                    is_cached_sample=False,
                    message=(
                        f"TNGIS portal connected for Survey {survey_number}/{subdivision or ''}, but owner/patta records were unavailable "
                        f"on the government map viewer. Toggle 'Edit Mode' below to enter verified records manually."
                    ),
                )
    except Exception as e:
        print(f"Live scraper execution notice: {e}")
    finally:
        if output_file.exists():
            try:
                output_file.unlink()
            except Exception:
                pass

    if is_sample_parcel(search_dict):
        return load_tngis_results(search_dict)

    return TngisLookupResponse(
        search=search_dict,
        owners=[],
        land_details=TngisLandDetails(),
        guideline_value=TngisGuidelineValue(),
        document_status=TngisDocumentStatus(),
        is_cached_sample=False,
        message=(
            f"Live scraper could not locate Survey {survey_number}/{subdivision or ''} in {village} on TNGIS portal (or request timed out). "
            f"Please toggle 'Edit Mode' below to enter verified owner and land details before saving."
        ),
    )


def get_scraper_dir() -> Path:
    """Locate the tngis_scraper directory."""
    candidates = [
        Path("..") / "tngis_scraper",
        Path("tngis_scraper"),
        Path(__file__).resolve().parent.parent.parent.parent / "tngis_scraper",
    ]
    for p in candidates:
        if p.exists() and (p / "tngis_scraper.py").exists():
            return p.resolve()
    return candidates[0].resolve()


def get_scraper_python() -> str:
    """Find a Python executable with selenium installed."""
    import shutil
    import sys
    try:
        import selenium  # noqa: F401
        return sys.executable
    except ImportError:
        pass
    candidates = [
        r"C:\Users\w\AppData\Local\Programs\Python\Python311\python.exe",
        shutil.which("python"),
        sys.executable,
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(Path(c).resolve())
    return sys.executable


def start_interactive_scrape(
    district: str,
    taluk: str,
    village: str,
    survey_number: str,
    subdivision: Optional[str] = None,
    area_type: str = "rural",
    headless: bool = True,
) -> str:
    """Launch tngis_scraper.py asynchronously with session tracking."""
    import json
    import subprocess
    import uuid

    session_id = uuid.uuid4().hex[:8]
    scraper_dir = get_scraper_dir()
    script_path = scraper_dir / "tngis_scraper.py"
    output_file = scraper_dir / f"tngis_run_{session_id}.txt"
    status_file = scraper_dir / f"tngis_status_{session_id}.json"
    log_file = scraper_dir / f"tngis_log_{session_id}.txt"

    # Write initial starting status
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump({
            "session_id": session_id,
            "status": "starting",
            "message": "Initializing live browser session...",
            "timestamp": time.time(),
        }, f)

    python_bin = get_scraper_python()
    cmd = [
        python_bin,
        "-u",
        str(script_path),
        "--district", district,
        "--taluk", taluk,
        "--village", village,
        "--survey", survey_number,
        "--subdiv", subdivision or "",
        "--area-type", area_type,
        "--session-id", session_id,
        "--output", str(output_file),
    ]
    if headless:
        cmd.append("--headless")

    log_fh = open(log_file, "w", encoding="utf-8")
    subprocess.Popen(
        cmd,
        cwd=str(scraper_dir),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    return session_id


def get_interactive_scrape_status(session_id: str) -> TngisScrapeStatusResponse:
    """Check live status of an interactive scraping session and return parsed data upon completion."""
    import json

    scraper_dir = get_scraper_dir()
    status_file = scraper_dir / f"tngis_status_{session_id}.json"
    log_file = scraper_dir / f"tngis_log_{session_id}.txt"

    if not status_file.exists():
        return TngisScrapeStatusResponse(
            session_id=session_id,
            status="starting",
            message="Initializing live browser session...",
        )

    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return TngisScrapeStatusResponse(
            session_id=session_id,
            status="starting",
            message="Reading scraper state...",
        )

    status = data.get("status", "starting")
    message = data.get("message", "Processing...")
    timestamp = data.get("timestamp")

    # Check for early process errors in log if still starting
    if status == "starting" and log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as lf:
                log_content = lf.read()
            if "Traceback (most recent call last)" in log_content:
                lines = [l.strip() for l in log_content.splitlines() if l.strip()]
                err_line = lines[-1] if lines else "Process failed on startup"
                return TngisScrapeStatusResponse(
                    session_id=session_id,
                    status="error",
                    message=f"Startup error: {err_line}",
                    extra={"log": log_content[-1000:]},
                )
        except Exception:
            pass

    map_image = data.get("map_image")
    if not map_image:
        map_file = scraper_dir / f"tngis_map_{session_id}.png"
        if map_file.exists():
            try:
                import base64
                with open(map_file, "rb") as mf:
                    b64 = base64.b64encode(mf.read()).decode("utf-8")
                    map_image = f"data:image/png;base64,{b64}"
            except Exception:
                pass

    lookup_data: Optional[TngisLookupResponse] = None

    if status == "completed":
        output_file = scraper_dir / f"tngis_run_{session_id}.txt"
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
            lookup_data = parse_tngis_content(content)
            lookup_data.is_cached_sample = False
            lookup_data.message = f"Live TNGIS revenue records successfully scraped and structured."
            save_to_survey_cache(lookup_data)

    return TngisScrapeStatusResponse(
        session_id=session_id,
        status=status,
        message=message,
        timestamp=timestamp,
        extra=data,
        map_image=map_image,
        data=lookup_data,
    )


def continue_interactive_scrape(session_id: str, x_ratio: float = 0.5, y_ratio: float = 0.5) -> bool:
    """Drop the continue signal file with coordinates to trigger panel extraction in tngis_scraper.py."""
    import json
    scraper_dir = get_scraper_dir()
    signal_file = scraper_dir / f"tngis_continue_{session_id}.signal"
    with open(signal_file, "w", encoding="utf-8") as f:
        json.dump({"x_ratio": x_ratio, "y_ratio": y_ratio}, f)
    return True
