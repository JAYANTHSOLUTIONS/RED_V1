import json
import os
from pathlib import Path
from fastapi.openapi.utils import get_openapi
from app.main import create_app

def test_openapi_schema_matches_frozen_snapshot():
    """Ensure the generated OpenAPI schema matches the frozen Phase 18 snapshot."""
    app = create_app()
    
    current_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    
    docs_dir = Path(os.path.dirname(__file__)) / ".." / ".." / "docs"
    snapshot_path = docs_dir / "openapi.json"
    
    assert snapshot_path.exists(), "OpenAPI snapshot does not exist."
    
    with open(snapshot_path, "r") as f:
        frozen_schema = json.load(f)
        
    # We compare the json representation to avoid minor type differences (e.g. tuple vs list)
    current_json = json.loads(json.dumps(current_schema))
    
    # If this fails, the API contract has drifted from the frozen snapshot.
    # Any changes must be explicitly reviewed and the snapshot updated.
    assert current_json == frozen_schema, "API contract has drifted from the frozen Phase 18 snapshot."
