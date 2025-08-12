import os, re
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

app = FastAPI(title="Assess Router")

# CORS (open for POC; restrict allow_origins in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# -------- Config --------
BASE = os.getenv("STATIC_BASE_URL", "https://assess-poc.onrender.com")

COURSE_URLS = {
    "product_architect":        f"{BASE}/product-architect.html",
    "domain_expert":            f"{BASE}/domain-expert.html",
    "pcb_designer":             f"{BASE}/pcb-designer.html",
    "integration_engineer":     f"{BASE}/integration-engineer.html",
    "procurement_specialist":   f"{BASE}/procurement-specialist.html",
    "mech_designer":            f"{BASE}/mech-designer.html",
    "product_manager":          f"{BASE}/product-manager.html",
    "firmware_developer":       f"{BASE}/firmware-developer.html",
}

# -------- Type-first routing (exact list you provided) --------
def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "")).strip().lower()

# normalized label -> internal course key
TYPE_MAP_NORM = {
    "product manager": "product_manager",
    "product designer": "product_architect",        # confirm if this should point elsewhere
    "procurement specialist": "procurement_specialist",
    "pcb designer": "pcb_designer",
    "mechanical designer": "mech_designer",
    "integration engineer": "integration_engineer",
    "firmware developer": "firmware_developer",
    "domain expert": "domain_expert",
}

def map_by_type(type_str: str | None) -> str | None:
    t = _norm(type_str)
    if not t:
        return None
    if t in TYPE_MAP_NORM:
        return TYPE_MAP_NORM[t]
    # tolerate variants like "Senior PCB Designer", "Lead Product Manager"
    for k, v in TYPE_MAP_NORM.items():
        if k in t:
            return v
    return None

# -------- Fallback keyword scorer (used only if type missing/unrecognized) --------
KEYWORDS = {
    "product_architect": {"keywords": ["system architecture","system architect","product architecture","requirements","specification","interface"]},
    "domain_expert": {"keywords": ["domain expert","subject matter expert","sme","compliance","regulatory","standards","iso","iec","ul"]},
    "pcb_designer": {"keywords": ["pcb","altium","allegro","orcad","layout","stackup","impedance","drc","gerber"]},
    "integration_engineer": {"keywords": ["integration","bring-up","hil","sil","system test","interoperability","can","spi","i2c","uart"]},
    "procurement_specialist": {"keywords": ["procurement","sourcing","vendor","supplier","rfq","purchase","costing","ppap","logistics"]},
    "mech_designer": {"keywords": ["mechanical design","cad","solidworks","creo","catia","gd&t","injection molding","fea","heatsink"]},
    "product_manager": {"keywords": ["product manager","roadmap","gtm","backlog","agile","scrum","stakeholder","kpi","user stories"]},
    "firmware_developer": {"keywords": ["firmware","embedded","rtos","mcu","stm32","ble","driver","bootloader","i2c","spi","uart","arm cortex"]},
}

def keyword_decide(text: str) -> str:
    t = text.lower()
    scores = {}
    for course, cfg in KEYWORDS.items():
        score = sum(len(re.findall(rf"\b{re.escape(kw.lower())}\b", t)) for kw in cfg["keywords"])
        scores[course] = score
    # fallback to most frequent; ties will be arbitrary but acceptable for fallback
    return max(scores, key=scores.get)

# -------- Routes --------
@app.get("/")
def root():
    return {"status": "ok", "usage": "/route?title=...&company=...&desc=...&type=<one of 8 types>"}

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/route")
@app.post("/route")
async def route(request: Request):
    if request.method == "GET":
        q = request.query_params
        title = q.get("title", "")
        company = q.get("company", "")
        desc = q.get("desc", "")
        job_type = q.get("type", "")
        debug = q.get("debug", "0") == "1"
    else:
        body = await request.json()
        title = body.get("title", "")
        company = body.get("company", "")
        desc = body.get("desc", "")
        job_type = body.get("type", "")
        debug = body.get("debug", False)

    # 1) Type-first
    course = map_by_type(job_type)
    via = "type"

    # 2) If type not provided/unrecognized, fallback to keywords
    if not course:
        via = "keywords"
        course = keyword_decide(" ".join([title, company, desc])[:20000])

    url = COURSE_URLS.get(course, BASE)

    if debug:
        return JSONResponse({"via": via, "type_value": job_type, "course": course, "redirect": url})

    # Always redirect (POC-friendly)
    return RedirectResponse(url=url, status_code=302)
