"""Third board probe: GCC employers. Writes tools/probe3.json.

1. Fetch each company's careers page and look for the hiring system behind it
   (Workday tenant/site, Greenhouse, Lever, Ashby, SmartRecruiters, Eightfold, Oracle, SuccessFactors, ...).
2. Try every Workday tenant found (plus guesses) with a "data engineer" search and count India hits.
3. Try the custom job APIs we would need for big employers (Amazon, Microsoft, Google, Goldman, JPMorgan,
   American Express, Tesco, Fidelity).
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

sys.path.insert(0, ".")
import companies  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
INDIA = re.compile(r"india|bangalore|bengaluru|hyderabad|pune|chennai|mumbai|gurgaon|gurugram|noida|delhi|kolkata", re.I)
T = 20

CAREERS = {
    "Walmart": "https://careers.walmart.com/",
    "Wells Fargo": "https://www.wellsfargojobs.com/",
    "Fidelity Investments": "https://jobs.fidelity.com/in/",
    "JPMorgan Chase": "https://careers.jpmorgan.com/in/en/home",
    "American Express": "https://www.americanexpress.com/en-us/careers/",
    "Goldman Sachs": "https://higher.gs.com/",
    "Tesco": "https://www.tesco-careers.com/",
    "Cargill": "https://careers.cargill.com/",
    "Best Buy": "https://jobs.bestbuy.com/",
    "Costco": "https://www.costco.com/jobs.html",
    "Mars": "https://careers.mars.com/",
    "Starbucks": "https://careers.starbucks.com/",
    "Walgreens": "https://jobs.walgreens.com/",
    "T-Mobile": "https://careers.t-mobile.com/",
    "JLL": "https://careers.jll.com/",
    "UBS": "https://www.ubs.com/global/en/careers.html",
    "CIBC": "https://careers.cibc.com/",
    "Smartsheet": "https://www.smartsheet.com/careers",
    "Blackstone": "https://www.blackstone.com/careers/",
    "Eli Lilly": "https://careers.lilly.com/",
    "Experian": "https://jobs.experian.com/",
    "Revolut": "https://www.revolut.com/careers/",
    "Unilever": "https://careers.unilever.com/",
    "PepsiCo": "https://www.pepsicojobs.com/",
    "Heineken": "https://careers.theheinekencompany.com/",
    "L'Oreal": "https://careers.loreal.com/",
    "Nestle": "https://www.nestle.com/jobs",
    "AB InBev": "https://www.ab-inbev.com/careers/",
    "IKEA": "https://jobs.ikea.com/",
    "H&M": "https://career.hm.com/",
    "Airbus": "https://www.airbus.com/en/careers",
    "Mercedes-Benz R&D India": "https://jobs.mercedes-benz.com/",
    "GE Vernova": "https://careers.gevernova.com/",
    "Amadeus": "https://jobs.amadeus.com/",
    "Southwest Airlines": "https://careers.southwestair.com/",
    "American Airlines": "https://jobs.aa.com/",
    "The Standard": "https://www.standard.com/careers",
    "AssetMark": "https://www.assetmark.com/careers",
    "CNH": "https://www.cnh.com/en-US/Careers",
    "N-able": "https://www.n-able.com/careers",
    "PUMA": "https://about.puma.com/en/careers",
    "o9 Solutions": "https://o9solutions.com/careers/",
    "Deepwatch": "https://www.deepwatch.com/careers/",
    "Nielsen": "https://careers.nielsen.com/",
    "Microsoft": "https://careers.microsoft.com/",
    "Amazon": "https://www.amazon.jobs/",
    "Google": "https://www.google.com/about/careers/applications/",
    "Abercrombie & Fitch": "https://corporate.abercrombie.com/careers/",
    "Sanofi": "https://jobs.sanofi.com/",
    "Airbnb": "https://careers.airbnb.com/",
}

# Workday guesses to try even if the careers page does not link them
WD_GUESS = [
    "walmart|5|WalmartExternal", "wf|1|WellsFargoJobs", "wellsfargo|1|WellsFargoJobs", "fmr|1|FidelityCareers",
    "cargill|5|External", "bestbuy|5|BestBuy", "mars|3|External", "starbucks|5|StarbucksExternal",
    "walgreens|5|External", "tmobile|1|External", "jll|1|jllcareers", "ubs|3|UBS_Experienced_Careers",
    "cibc|3|search", "blackstone|1|Blackstone_Careers", "lilly|1|LLY", "costco|5|Costco_Careers",
    "experian|5|ExperianCareers", "assetmark|5|AssetMark", "cnh|3|CNH_Careers", "ge|5|GE_ExternalSite",
]

PATTERNS = {
    "workday": r"([\w-]+)\.wd(\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)",
    "greenhouse": r"(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)",
    "lever": r"jobs\.lever\.co/([\w.-]+)",
    "ashby": r"jobs\.ashbyhq\.com/([\w.%-]+)",
    "smartrecruiters": r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)",
    "eightfold": r"([\w-]+)\.eightfold\.ai",
    "oracle": r"([\w-]+)\.fa\.([\w-]+)\.oraclecloud\.com",
    "successfactors": r"(career\d*\.successfactors\.(?:com|eu)|[\w-]+\.jobs2web\.com)",
    "phenom": r"(cdn\.phenompeople\.com|phenom)",
    "icims": r"([\w-]+)\.icims\.com",
    "taleo": r"([\w-]+)\.taleo\.net",
    "avature": r"([\w-]+\.avature\.net)",
    "radancy": r"(tmpwebeng|radancy|jobs\.[\w-]+\.com/search-jobs)",
    "tribepad": r"(tribepad)",
}


def get(url, **kw):
    return requests.get(url, headers=UA, timeout=T, allow_redirects=True, **kw)


def scan_page(name, url):
    out = {"url": url}
    try:
        r = get(url)
        out["status"] = r.status_code
        out["final"] = r.url
        text = r.text[:600000]
        found = {}
        for k, p in PATTERNS.items():
            m = re.findall(p, text, re.I)
            if m:
                found[k] = sorted({"|".join(x) if isinstance(x, tuple) else x for x in m})[:6]
        out["found"] = found
    except Exception as e:  # noqa: BLE001
        out["error"] = type(e).__name__
    return name, out


def wd_try(slug):
    tenant, wd, site = slug.split("|")
    api = f"https://{tenant}.wd{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    try:
        r = requests.post(api, json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "data engineer"},
                          headers={**UA, "Accept": "application/json", "Content-Type": "application/json"}, timeout=T)
        if r.status_code != 200:
            return slug, {"status": r.status_code}
        d = r.json()
        posts = d.get("jobPostings") or []
        return slug, {"status": 200, "total": d.get("total"),
                      "india": sum(1 for p in posts if INDIA.search(p.get("locationsText") or "")),
                      "sample": [(p.get("title"), p.get("locationsText")) for p in posts[:5]]}
    except Exception as e:  # noqa: BLE001
        return slug, {"error": type(e).__name__}


def api_try(name, method, url, **kw):
    try:
        r = requests.request(method, url, headers={**UA, **kw.pop("headers", {})}, timeout=T, **kw)
        out = {"status": r.status_code, "final": r.url, "ctype": r.headers.get("content-type", "")}
        body = r.text
        out["len"] = len(body)
        if "json" in out["ctype"]:
            try:
                d = r.json()
                out["keys"] = list(d.keys())[:15] if isinstance(d, dict) else f"list[{len(d)}]"
                out["head"] = json.dumps(d)[:1500]
            except ValueError:
                out["head"] = body[:800]
        else:
            out["head"] = body[:400]
            out["india_mentions"] = len(INDIA.findall(body))
            out["data_engineer_mentions"] = len(re.findall(r"data engineer", body, re.I))
        return name, out
    except Exception as e:  # noqa: BLE001
        return name, {"error": type(e).__name__}


APIS = [
    ("amazon", "GET", "https://www.amazon.jobs/en/search.json?base_query=data%20engineer&loc_query=India&country=IND&result_limit=10&offset=0"),
    ("microsoft_gcs", "GET", "https://gcsservices.careers.microsoft.com/search/api/v1/search?q=data%20engineer&lc=India&l=en_us&pg=1&pgSz=20&o=Recent"),
    ("microsoft_eightfold", "GET", "https://apply.careers.microsoft.com/api/apply/v2/jobs?domain=microsoft.com&query=data%20engineer&location=India&start=0&num=10"),
    ("microsoft_pcsx", "GET", "https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=data%20engineer&location=India&start=0"),
    ("google_html", "GET", "https://www.google.com/about/careers/applications/jobs/results/?q=%22data%20engineer%22&location=India"),
    ("google_v3", "GET", "https://careers.google.com/api/v3/search/?q=data%20engineer&location=India"),
    ("amex_eightfold", "GET", "https://aexp.eightfold.ai/api/apply/v2/jobs?domain=aexp.com&query=data&location=India&start=0&num=10"),
    ("amex_careers", "GET", "https://aexp.eightfold.ai/careers?query=data&location=India"),
    ("jpmc_oracle", "GET", "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber=CX_1001,keyword=%22data%20engineer%22,limit=10,offset=0,sortBy=POSTING_DATES_DESC"),
    ("goldman_html", "GET", "https://higher.gs.com/results?query=data%20engineer&location=India"),
    ("goldman_graphql", "POST", "https://api-higher.gs.com/gateway/api/v1/graphql"),
    ("tesco_avature", "GET", "https://careers.tesco.com/en_GB/careers/SearchJobs/data?listFilterMode=1"),
    ("tesco_avature_feed", "GET", "https://careers.tesco.com/en_GB/careers/SearchJobs/feed/?keyword=data"),
    ("tesco_tribepad", "GET", "https://www.tesco-careers.com/search-and-apply/?keywords=data&location=Bengaluru"),
    ("fidelity_search", "GET", "https://jobs.fidelity.com/in/search-jobs/?keyword=data"),
    ("fidelity_india", "GET", "https://india.fidelity.com/search-jobs?keyword=data"),
    ("shell_radancy", "GET", "https://jobs.shell.com/search-jobs/data/India"),
    ("revolut_api", "GET", "https://www.revolut.com/api/careers/jobs"),
]

GOLDMAN_Q = {"operationName": "GetRoles", "variables": {"searchQueryInput": {"page": {"pageSize": 10, "pageNumber": 0},
             "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"}, "filters": [], "experiences": ["PROFESSIONAL"],
             "searchTerm": "data engineer"}},
             "query": "query GetRoles($searchQueryInput: RoleSearchQueryInput!) { roleSearch(searchQueryInput: $searchQueryInput) "
                      "{ totalCount items { roleId jobTitle externalSource { sourceId } locations { city country } } } }"}

GH_LIKE = {
    "greenhouse": lambda s: f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs",
    "lever": lambda s: f"https://api.lever.co/v0/postings/{s}?mode=json",
    "ashby": lambda s: f"https://api.ashbyhq.com/posting-api/job-board/{s}",
    "smartrecruiters": lambda s: f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100",
}
BOARD_GUESS = [("greenhouse", "smartsheet"), ("greenhouse", "deepwatch"), ("greenhouse", "o9solutions"),
               ("lever", "o9solutions"), ("lever", "nielsen"), ("greenhouse", "nielsen"), ("smartrecruiters", "Experian"),
               ("greenhouse", "revolut"), ("lever", "revolut"), ("greenhouse", "nable"), ("lever", "deepwatch"),
               ("ashby", "deepwatch"), ("smartrecruiters", "Unilever"), ("smartrecruiters", "IKEA"),
               ("smartrecruiters", "HMGroup"), ("smartrecruiters", "AbInBev"), ("smartrecruiters", "Puma"),
               ("smartrecruiters", "WesternDigital"), ("greenhouse", "airbnb")]


def board_try(kind, slug):
    try:
        r = requests.get(GH_LIKE[kind](slug), headers=UA, timeout=T)
        if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            return f"{kind}:{slug}", {"status": r.status_code}
        d = r.json()
        if kind == "lever":
            titles = [(j.get("text"), (j.get("categories") or {}).get("location")) for j in d]
        elif kind == "smartrecruiters":
            titles = [(j.get("name"), (j.get("location") or {}).get("city")) for j in d.get("content", [])]
        else:
            titles = [(j.get("title"), (j.get("location") or {}).get("name") if isinstance(j.get("location"), dict) else j.get("location"))
                      for j in d.get("jobs", [])]
        return f"{kind}:{slug}", {"status": 200, "count": len(titles),
                                  "india": sum(1 for _, l in titles if INDIA.search(str(l or ""))),
                                  "sample": titles[:5]}
    except Exception as e:  # noqa: BLE001
        return f"{kind}:{slug}", {"error": type(e).__name__}


def main():
    res = {"run": int(time.time())}
    with ThreadPoolExecutor(max_workers=8) as pool:
        res["pages"] = dict(pool.map(lambda kv: scan_page(*kv), CAREERS.items()))
    found_wd = set(WD_GUESS)
    for v in res["pages"].values():
        for w in (v.get("found") or {}).get("workday", []):
            found_wd.add(w)
    have = {s for s, _, _ in companies.WORKDAY}
    found_wd -= have
    with ThreadPoolExecutor(max_workers=6) as pool:
        res["workday"] = dict(pool.map(wd_try, sorted(found_wd)))
    out = {}
    for name, method, url in APIS:
        kw = {}
        if name == "goldman_graphql":
            kw = {"json": GOLDMAN_Q, "headers": {"Content-Type": "application/json", "Origin": "https://higher.gs.com"}}
        out[name] = api_try(name, method, url, **kw)[1]
        time.sleep(0.5)
    res["apis"] = out
    with ThreadPoolExecutor(max_workers=6) as pool:
        res["boards"] = dict(pool.map(lambda kv: board_try(*kv), BOARD_GUESS))
    with open("tools/probe3.json", "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    print(json.dumps({k: (len(v) if isinstance(v, dict) else v) for k, v in res.items()}))


if __name__ == "__main__":
    main()
