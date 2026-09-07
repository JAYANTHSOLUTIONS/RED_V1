import inspect
import json
import os
import sys
from pathlib import Path

# Add backend dir to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.routing import APIRoute
from fastapi.openapi.utils import get_openapi
from app.main import create_app

def extract_dependencies(route):
    deps = []
    
    # Check dependencies in route.dependant
    if hasattr(route, "dependant") and route.dependant.dependencies:
        for d in route.dependant.dependencies:
            call = d.call
            if hasattr(call, "__name__"):
                deps.append(call.__name__)
            elif type(call).__name__ == "function" and "require_roles" in str(call):
                deps.append("require_roles")
                
    # Also check dependencies that are classes/factories
    # specifically, `require_roles` returns a function, so it's named 'role_checker' usually
    # Let's just look at the signature of route.endpoint
    sig = inspect.signature(route.endpoint)
    for param in sig.parameters.values():
        if hasattr(param.default, "dependency"):
            dep_func = param.default.dependency
            if hasattr(dep_func, "__name__"):
                deps.append(dep_func.__name__)
                if dep_func.__name__ == "role_checker" or dep_func.__name__ == "require_roles":
                    deps.append("require_roles")
            else:
                 if "require_roles" in str(dep_func):
                    deps.append("require_roles")
                    
    # Also look for `current_user` param specifically in RED_V1 it's tied to auth
    if "current_user" in sig.parameters:
        deps.append("get_current_user")
        
    # Also look at router.dependencies if set
    if hasattr(route, "dependencies"):
        for d in route.dependencies:
            if hasattr(d.dependency, "__name__"):
                deps.append(d.dependency.__name__)

    return deps

def get_auth_info(dependencies):
    auth_required = False
    roles = []
    
    # simple heuristic
    if "get_current_user" in dependencies or "require_roles" in dependencies or "role_checker" in dependencies:
        auth_required = True
        
    if "require_roles" in dependencies or "role_checker" in dependencies:
        roles = ["CONSULTANT"]
        
    return auth_required, roles

def main():
    os.environ["APP_ENV"] = "local"
    app = create_app()
    
    # 1. Generate OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    
    docs_dir = Path(os.path.join(os.path.dirname(__file__), '..', 'docs'))
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    with open(docs_dir / "openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)

    # 2. Generate API Inventory
    inventory_lines = [
        "# API INVENTORY",
        "",
        "This document is automatically generated from the FastAPI application routes.",
        "",
        "| Method | Path | Summary | Operation ID | Auth | Roles |",
        "|--------|------|---------|--------------|------|-------|"
    ]
    
    auth_matrix_lines = [
        "# API AUTHORIZATION MATRIX",
        "",
        "This document is automatically generated.",
        "",
        "| Method | Path | Public/Auth | Roles | Notes |",
        "|--------|------|-------------|-------|-------|"
    ]

    for route in app.routes:
        if isinstance(route, APIRoute):
            method = list(route.methods)[0]
            path = route.path
            summary = route.summary or ""
            op_id = route.operation_id or route.name
            
            deps = extract_dependencies(route)
            auth_req, roles = get_auth_info(deps)
            
            auth_str = "Yes" if auth_req else "No"
            roles_str = ", ".join(roles) if roles else "-"
            
            inventory_lines.append(f"| {method} | `{path}` | {summary} | `{op_id}` | {auth_str} | {roles_str} |")
            
            auth_type = "Authenticated" if auth_req else "Public"
            if roles:
                auth_type = "Role-protected"
            
            auth_matrix_lines.append(f"| {method} | `{path}` | {auth_type} | {roles_str} | |")

    with open(docs_dir / "API_INVENTORY.md", "w") as f:
        f.write("\n".join(inventory_lines))
        
    with open(docs_dir / "API_AUTHORIZATION_MATRIX.md", "w") as f:
        f.write("\n".join(auth_matrix_lines))
        
    print("Successfully generated API documentation.")

if __name__ == "__main__":
    main()
