import os, re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

app = FastAPI(title="Assess Router POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# ---- Keyword map tuned to your 8 courses ----
KEYWORDS = {
    "product_architect": {
        "weight": 1.0,
        "keywords": [
            "system architecture","system architect","product architecture",
            "requirements","tradeoff","platform","scalability","roadmap",
            "interface definition","api design","specification","solution architecture"
        ],
        "boost_tools": ["uml","sysml","enterprise architect","sparx","doors","confluence","jira"]
    },
    "domain_expert": {
        "weight": 1.0,
        "keywords": [
            "domain expert","subject matter expert","sme",
            "compliance","standards","regulatory","certification","safety","reliability",
            "industry best practices","functional safety","iso","iec","ansi","ul","bis"
        ],
        "boost_tools": ["dfmea","pfmea","fta","fmeca","hazop","sils","aspice","iso 26262","iec 60601"]
    },
    "pcb_designer": {
        "weight": 1.2,
        "keywords": [
            "pcb","layout","footprint","stackup","impedance","drc","dfm","dfa","gerber","bom",
            "altium","allegro","orcad","pads","kicad","si","pi","high speed routing","length matching"
        ],
        "boost_tools": ["altium","allegro","orcad","pads","kicad","hyperlynx","ads","hfss"]
    },
    "integration_engineer": {
        "weight": 1.1,
        "keywords": [
            "integration","bring-up","system integration","hardware integration","software integration",
            "hIL","sIL","system test","integration test","interface testing","interoperability",
            "can","lin","ethernet","modbus","spi","i2c","uart","rs485","jtag","boundary scan"
        ],
        "boost_tools": ["vector canoe","canalyzer","labview","teststand","ni","dspace","raspberry pi","arduino"]
    },
    "procurement_specialist": {
        "weight": 1.0,
        "keywords": [
            "procurement","sourcing","vendor","supplier","rfq","rfx","purchase","costing","negotiation",
            "lead time","inventory","logistics","supply chain","bom validation","ppap","rohs","reach"
        ],
        "boost_tools": ["sap","oracle","ariba","zoho inventory","tally","ms excel","vlookup","power bi"]
    },
    "mech_designer": {
        "weight": 1.0,
        "keywords": [
            "mechanical design","cad","3d modeling","gd&t","tolerance stack-up","sheet metal",
            "injection molding","dfm","fea","thermal","heatsink","enclosure","fasteners"
        ],
        "boost_tools": ["solidworks","creo","nx","catia","ansys mechanical","autocad","fusion 360"]
    },
    "product_manager": {
        "weight": 0.9,
        "keywords": [
            "product manager","roadmap","prioritization","kpi","market research","stakeholder",
            "go-to-market","gtm","backlog","agile","scrum","user stories","acceptance criteria"
        ],
        "boost_tools": ["jira","confluence","mixpanel","google analytics","power bi","tableau"]
    },
    "firmware_developer": {
        "weight": 1.2,
        "keywords": [
            "firmware","embedded","mcu","rtos","bare metal","device driver","bootloader",
            "i2c","spi","uart","can","modbus","ble","arm cortex","stm32","nrf52","esp32",
            "memory map","interrupt","isr","linker script"
        ],
        "boost_tools": ["keil","iar","stm32cube","platformio","segger","jlink","openocd","git"]
    }
}

MIN_SCORE = 2.0
MARGIN = 1.0

def score_course(text: str, course_key: str) -> float:
    cfg = KEYWORDS[course_key]
    base = cfg.get("weight", 1.0)
    score = 0.0

    # keyword hits (phrases allowed)
    for kw in cfg["keywords"]:
        hits = len(re.findall(rf"\b{re.escape(kw.lower())}\b", text))
        score += hits * 1.0

    # tool/acronym boosts
    for tool in cfg.get("boost_tools", []):
        hits = len(re.findall(rf"\b{re.escape(tool.lower())}\b", text))
        score += hits * 1.5

    return base * score

def decide(text: str):
    t = text.lower()
    scores = {k: score_course(t, k) for k in KEYWORDS}
    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:2]
    (k1, s1), (k2, s2) = top[0], (top[1] if len(top) > 1 else (None, 0))
    confident = s1 >= MIN_SCORE and (s1 - s2) >= MARGIN
    return {"k1": k1, "s1": s1, "k2": k2, "s2": s2, "confident": confident, "scores": scores}

@app.get("/route")
@app.post("/route")
async def route(request: Request):
    """
    GET:  /route?title=...&company=...&desc=...&debug=1
    POST: { "title": "...", "company": "...", "desc": "...", "debug": false }
    """
    if request.method == "GET":
        q = request.query_params
        title = q.get("title", "")
        company = q.get("company", "")
        desc = q.get("desc", "")
        debug = q.get("debug", "0") == "1"
    else:
        body = await request.json()
        title = body.get("title", "")
        company = body.get("company", "")
        desc = body.get("desc", "")
        debug = body.get("debug", False)

    text = " ".join([title, company, desc])[:20000]
    result = decide(text)
    url = COURSE_URLS[result["k1"]]

    if debug or not result["confident"]:
        return JSONResponse({
            "decision": "auto" if result["confident"] else "low_confidence",
            "redirect": url, "top1": [result["k1"], result["s1"]],
            "top2": [result["k2"], result["s2"]], "scores": result["scores"]
        })
    return RedirectResponse(url=url, status_code=302)
