import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

app = FastAPI(title="Assess Router POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = os.getenv("STATIC_BASE_URL", "https://assess-poc.onrender.com")

# ---- Mapping from internal keys to static HTML URLs ----
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

# ---- Direct match mapping from Adzuna job type to course key ----
TYPE_MAP = {
    "Domain Expert": "domain_expert",
    "Firmware Developer": "firmware_developer",
    "Product Designer": "product_architect",   # Assuming this matches your "product_architect"
    "Procurement Engineer": "procurement_specialist",
    "PCB Design Engineer": "pcb_designer",
    "Mechanical Designer": "mech_designer",
    "Integration Engineer": "integration_engineer",
}

# ---- Keyword fallback (only if type not in TYPE_MAP) ----
import re
KEYWORDS = {
    "product_architect": {
        "keywords": ["system architecture","system architect","product architecture","requirements"],
    },
    "domain_expert": {
        "keywords": ["domain expert","subject matter expert","sme","compliance","standards"],
    },
    "pcb_designer": {
        "keywords": ["pcb","layout","footprint","stackup","impedance","drc","dfm"],
    },
    "integration_engineer": {
        "keywords": ["integration","bring-up","system integration","hardware integration","software integration"],
    },
    "procurement_specialist": {
        "keywords": ["procurement","sourcing","vendor","supplier","rfq","purchase","costing"],
    },
    "mech_designer": {
        "keywords": ["mechanical design","cad","3d modeling","gd&t","tolerance stack-up","sheet metal"],
    },
    "product_manager": {
        "keywords": ["product manager","roadmap","prioritization","kpi","market research"],
    },
    "firmware_developer": {
        "keywords": ["firmware","embedded","mcu","rtos","bare metal","device driver","bootloader"],
    }
}

def keyword_score(text: str):
    t = text.lower()
    scores = {}
    for course, cfg in KEYWORDS.items():
        score = sum(len(re.findall(rf"\b{re.escape(kw.lower())}\b", t)) for kw in cfg["keywords"])
        scores[course] = score
    top = max(scores, key=scores.get)
    return top

@app.get("/route")
async def route(request: Request):
    q = request.query_params
    title = q.get("title", "")
    company = q.get("company", "")
    desc = q.get("desc", "")
    job_type = q.get("type", "")  # exact Adzuna type
    debug = q.get("debug", "0") == "1"

    # 1) Try direct mapping first
    course = TYPE_MAP.get(job_type.strip(), None)

    # 2) If no match, fall back to keyword scoring
    if not course:
        course = keyword_score(" ".join([title, company, desc]))

    url = COURSE_URLS.get(course, BASE)  # fallback to BASE

    if debug:
        return JSONResponse({
            "via": "type" if job_type in TYPE_MAP else "keywords",
            "type_value": job_type,
            "redirect": url,
            "course": course
        })

    return RedirectResponse(url=url, status_code=302)
