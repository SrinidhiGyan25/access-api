import os, re
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

app = FastAPI(title="Assess Router – Type Only")

# CORS (open for POC; restrict to your site origin in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------- Config ----------------
# Your static site base (Render Static Site URL or your custom domain)
BASE = os.getenv("STATIC_BASE_URL", "https://assess-poc.onrender.com")

COURSE_URLS = {
    "domain_expert":            f"{BASE}/domain-expert.html",
    "firmware_developer":       f"{BASE}/firmware-developer.html",
    "integration_engineer":     f"{BASE}/integration-engineer.html",
    "mech_designer":            f"{BASE}/mech-designer.html",
    "pcb_designer":             f"{BASE}/pcb-designer.html",
    "procurement_specialist":   f"{BASE}/procurement-specialist.html",
    "product_architect":        f"{BASE}/product-architect.html",
    "product_manager":          f"{BASE}/product-manager.html",
}

# Normalizer for incoming type/mainJOB strings
def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "")).strip().lower()

# Exact 8 roles from your sheet → internal course key
TYPE_MAP = {
    "domain expert":            "domain_expert",
    "firmware developer":       "firmware_developer",
    "integration engineer":     "integration_engineer",
    "mechanical designer":      "mech_designer",
    "pcb designer":             "pcb_designer",
    "procurement specialist":   "procurement_specialist",
    "product designer":         "product_architect",   # per your decision
    "product manager":          "product_manager",
}

def map_type_to_url(type_str: str | None) -> str | None:
    t = _norm(type_str)  # lowercase + strip
    if not t:
        return None
    # exact normalized match
    if t in TYPE_MAP:
        return COURSE_URLS[TYPE_MAP[t]]
    # tolerate mild variants like "Senior PCB Designer"
    for label, key in TYPE_MAP.items():
        if label in t:
            return COURSE_URLS[key]
    return None

# ---------------- Routes ----------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "usage": "/route?title=...&company=...&desc=...&type=<mainJOB>",
        "types": list(TYPE_MAP.keys()),
    }

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/route")
async def route(request: Request):
    """
    Required query param:
      - type : one of the 8 main job roles (Domain Expert, Firmware Developer, ...)

    Other params (title/company/desc) are ignored here (kept for future use).
    """
    q = request.query_params
    job_type = q.get("type", "")
    debug = q.get("debug", "0") == "1"

    url = map_type_to_url(job_type)

    if not url:
        # If unknown type -> return helpful JSON (or redirect to index if you prefer)
        payload = {
            "error": "unknown_type",
            "received": job_type,
            "expected_one_of": list(TYPE_MAP.keys()),
        }
        return JSONResponse(payload, status_code=400)

    if debug:
        return JSONResponse({"via": "type", "type_value": job_type, "redirect": url})

    return RedirectResponse(url=url, status_code=302)
