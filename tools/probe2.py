"""Second board probe. Writes tools/probe2.json.

1. Companies from the remoteintech/remote-jobs list that hire worldwide or in Asia-Pacific
   (tools/remote_companies.json), checked on 8 hiring systems.
2. Workday career sites of large companies with India tech centres.
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests

sys.path.insert(0, ".")
import companies  # noqa: E402

UA = {"User-Agent": "shoreless.dev/1.0 (board probe)"}
DATA = re.compile(r"\bdata\b|analytics|\betl\b|\bbi\b|business intelligence|warehouse", re.I)
INDIA = re.compile(r"india|bangalore|bengaluru|hyderabad|pune|chennai|mumbai|gurgaon|gurugram|noida|delhi|kolkata", re.I)
HAVE = {s.lower() for lst in (companies.GREENHOUSE, companies.LEVER, companies.ASHBY, companies.SMARTRECRUITERS, companies.WORKABLE)
        for s, _, _ in lst}


def get(url, **kw):
    return requests.get(url, headers=UA, timeout=15, **kw)


# ---------- part 1: remote-first companies on 8 hiring systems ----------

def titles_json(path_fn):
    def f(slug):
        r = get(path_fn[0](slug))
        if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            return None
        return path_fn[1](r.json())
    return f


def personio(slug):
    for tld in ("de", "com"):
        r = get(f"https://{slug}.jobs.personio.{tld}/xml")
        if r.status_code == 200 and "<position" in r.text:
            return re.findall(r"<name>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</name>", r.text)
    return None


def teamtailor(slug):
    r = get(f"https://{slug}.teamtailor.com/jobs.rss")
    if r.status_code == 200 and "<rss" in r.text[:500]:
        return re.findall(r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", r.text, re.S)
    return None


ATS = {
    "greenhouse": titles_json((lambda s: f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs", lambda d: [j["title"] for j in d.get("jobs", [])])),
    "lever": titles_json((lambda s: f"https://api.lever.co/v0/postings/{s}?mode=json", lambda d: [j["text"] for j in d] if isinstance(d, list) else None)),
    "ashby": titles_json((lambda s: f"https://api.ashbyhq.com/posting-api/job-board/{s}", lambda d: [j["title"] for j in d.get("jobs", [])])),
    "workable": titles_json((lambda s: f"https://apply.workable.com/api/v1/widget/accounts/{s}", lambda d: [j["title"] for j in d.get("jobs", [])])),
    "smartrecruiters": titles_json((lambda s: f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100", lambda d: [j["name"] for j in d.get("content", [])] or None)),
    "recruitee": titles_json((lambda s: f"https://{s}.recruitee.com/api/offers/", lambda d: [j["title"] for j in d.get("offers", [])])),
    "personio": personio,
    "teamtailor": teamtailor,
}
FROM_URL = [
    ("greenhouse", r"greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)"),
    ("lever", r"jobs\.lever\.co/([\w.-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([\w.%-]+)"),
    ("workable", r"(?:apply\.)?workable\.com/([\w-]+)"),
    ("smartrecruiters", r"smartrecruiters\.com/([\w-]+)"),
    ("recruitee", r"([\w-]+)\.recruitee\.com"),
    ("personio", r"([\w-]+)\.jobs\.personio\.(?:de|com)"),
    ("teamtailor", r"([\w-]+)\.teamtailor\.com"),
]


def variants(c):
    out = []
    for u in (c.get("careers"), c.get("site")):
        for ats, rx in FROM_URL:
            m = re.search(rx, u or "", re.I)
            if m:
                out.append((ats, m.group(1)))
    names = {c.get("slug") or "", re.sub(r"[^a-z0-9]", "", (c.get("name") or "").lower()),
             re.sub(r"[^a-z0-9]+", "-", (c.get("name") or "").lower()).strip("-")}
    host = urlparse(c.get("site") or "").netloc.lower().removeprefix("www.")
    if host:
        names.add(host.split(".")[0])
    names = {n for n in names if len(n) >= 2}
    exact = {a for a, _ in out}
    out += [(a, n) for n in names for a in ATS if a not in exact]
    return list(dict.fromkeys(out))


def probe(args):
    c, ats, slug = args
    if slug.lower() in HAVE:
        return None
    try:
        t = ATS[ats](slug)
    except Exception:  # noqa: BLE001
        return None
    if not t:
        return None
    return {"company": c["name"], "region": c["region"], "ats": ats, "slug": slug, "jobs": len(t),
            "data_jobs": sum(1 for x in t if DATA.search(x)), "sample": [x for x in t if DATA.search(x)][:4]}


# ---------- part 2: Workday ----------

WORKDAY = {  # tenant: (preferred wd host number, preferred site) — guesses are checked below
    "nvidia": (5, "NVIDIAExternalCareerSite"), "salesforce": (12, "External_Career_Site"), "adobe": (5, "external_experienced"),
    "intel": (1, "External"), "walmart": (5, "WalmartExternal"), "target": (5, "targetcareers"), "mastercard": (1, "CorporateCareers"),
    "paypal": (1, "jobs"), "dell": (1, "External"), "hp": (5, "ExternalCareerSite"), "autodesk": (1, "Ext"), "workday": (5, "Workday"),
    "broadcom": (1, "External_Career"), "micron": (1, "External"), "amgen": (1, "Careers"), "blueyonder": (5, "BlueYonderCareers"),
    "jda": (5, "JDACareers"), "maersk": (3, "Maersk_Careers"), "thomsonreuters": (5, "External_Career_Site"), "3m": (1, "Search"),
    "zebra": (1, "Zebra_Careers"), "wk": (3, "External"), "astrazeneca": (3, "Careers"), "novartis": (3, "Novartis_Careers"),
    "gsk": (5, "GSKCareers"), "pfizer": (1, "PfizerCareers"), "philips": (3, "jobs-and-careers"), "chevron": (5, "jobs"),
    "nike": (1, "nke"), "disney": (5, "disneycareer"), "comcast": (5, "Comcast_Careers"), "capitalone": (12, "Capital_One"),
    "ms": (5, "External"), "statestreet": (1, "Global"), "bnymellon": (5, "BNY_Mellon_Careers"), "citi": (5, "2"),
    "amat": (1, "External"), "kyndryl": (5, "KyndrylProfessionalCareers"), "lowes": (5, "LWS_External_CS"),
    "fedex": (1, "FXE-LAC_External_Career_Site"), "ups": (5, "UPS"), "honeywell": (5, "Honeywell"), "carrier": (5, "jobs"),
    "gartner": (5, "EXT"), "marriott": (5, "Marriott"), "expedia": (5, "search"), "unilever": (3, "Unilever"),
    "sanofi": (3, "SanofiCareers"), "bayer": (3, "Bayer"), "mondelez": (3, "External"), "kenvue": (1, "kenvue"),
    "manh": (5, "Manhattan"), "manhattanassociates": (5, "External"), "kinaxis": (3, "Kinaxis"), "e2open": (1, "E2open"),
    "descartes": (3, "Descartes"), "zf": (3, "zf_careers"), "dhl": (3, "DHL"), "db": (3, "DBWebsite"), "barclays": (3, "External_Career_Site_Barclays"),
    "hsbc": (3, "external"), "wellsfargo": (1, "WellsFargoJobs"), "fidelity": (1, "FidelityCareers"), "equinix": (1, "External"),
    "rakuten": (1, "RakutenCareers"), "flex": (1, "Careers"), "ti": (1, "TI"), "lamresearch": (5, "LAM"), "synopsys": (1, "careers"),
    "cadence": (1, "External_Careers"), "servicenow": (1, "ServiceNow"), "athenahealth": (1, "External"), "optum": (5, "Optum"),
    "elevancehealth": (1, "ANT"), "cvshealth": (1, "CVS_Health_Careers"), "pg": (5, "1000"), "pepsico": (5, "PepsiCo"),
    "loreal": (3, "LOreal"), "abbott": (5, "abbottcareers"), "medtronic": (1, "MedtronicCareers"), "ge": (5, "GE"),
    "gehealthcare": (5, "GEHC_ExternalSite"), "siemens": (3, "Siemens"), "bosch": (3, "Bosch"), "shell": (3, "ShellCareers"),
    "bp": (3, "bpCareers"), "accenture": (3, "AccentureCareers"), "ey": (5, "EY"), "kpmg": (5, "KPMG"), "deloitte": (5, "Deloitte"),
}
SITES = ["External", "Careers", "careers", "External_Career_Site", "ExternalCareerSite", "jobs", "Search", "{T}Careers", "{T}_Careers",
         "{T}External", "{T}", "External_Careers", "en-US"]
WDS = [1, 3, 5, 12, 103]


def wd_search(tenant, wd, site, text="data engineer"):
    url = f"https://{tenant}.wd{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    r = requests.post(url, json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": text},
                      headers={**UA, "Accept": "application/json", "Content-Type": "application/json"}, timeout=15)
    if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        return None
    return r.json()


def wd_probe(tenant):
    wd0, site0 = WORKDAY[tenant]
    tries = [(wd0, site0)] + [(w, s.replace("{T}", tenant.capitalize() if s.startswith("{T}") else tenant)) for w in WDS for s in SITES]
    for wd, site in dict.fromkeys(tries):
        try:
            d = wd_search(tenant, wd, site)
        except Exception:  # noqa: BLE001
            continue
        if d is None:
            continue
        posts = d.get("jobPostings") or []
        try:
            di = wd_search(tenant, wd, site, "data India") or {}
        except Exception:  # noqa: BLE001
            di = {}
        india = [p for p in (di.get("jobPostings") or []) if INDIA.search(p.get("locationsText") or "")]
        return {"tenant": tenant, "wd": wd, "site": site, "data_total": d.get("total"), "india_data_sample": len(india),
                "sample": [f"{p.get('title')} | {p.get('locationsText')}" for p in (india or posts)[:5]]}
    return {"tenant": tenant, "found": False}


if __name__ == "__main__":
    t0 = time.time()
    cos = json.load(open("tools/remote_companies.json"))
    tasks = [(c, a, s) for c in cos for a, s in variants(c)]
    with ThreadPoolExecutor(max_workers=24) as pool:
        hits = [h for h in pool.map(probe, tasks) if h]
    best = {}
    for h in hits:  # one board per company and system
        k = (h["company"], h["ats"])
        if k not in best or h["jobs"] > best[k]["jobs"]:
            best[k] = h
    hits = sorted(best.values(), key=lambda h: (-h["data_jobs"], -h["jobs"]))
    with ThreadPoolExecutor(max_workers=8) as pool:
        wd = list(pool.map(wd_probe, WORKDAY))
    json.dump({"boards": hits, "workday": wd, "companies": len(cos), "checks": len(tasks), "seconds": int(time.time() - t0)},
              open("tools/probe2.json", "w"), indent=1)
    print(f"{len(hits)} boards from {len(cos)} companies ({len(tasks)} checks); "
          f"workday {sum(1 for w in wd if w.get('site'))}/{len(wd)} found; {time.time() - t0:.0f}s")
