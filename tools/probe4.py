"""Fourth probe: details for the custom job APIs. Writes tools/probe4.json."""
import json
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
T = 25
ORC = "/hcmRestApi/resources/latest/recruitingCEJobRequisitions"


def req(method, url, **kw):
    try:
        r = requests.request(method, url, headers={**UA, **kw.pop("headers", {})}, timeout=T, **kw)
        return {"status": r.status_code, "final": r.url, "ctype": r.headers.get("content-type", ""), "body": r.text}
    except Exception as e:  # noqa: BLE001
        return {"error": type(e).__name__}


def clip(d, n=4000):
    d = dict(d)
    if "body" in d:
        d["body"] = d["body"][:n]
    return d


res = {}

# Oracle: JPMorgan with location facets, then India location id
res["jpmc_facets"] = clip(req("GET", "https://jpmc.fa.oraclecloud.com" + ORC +
                              "?onlyData=true&expand=requisitionList.secondaryLocations,flexFieldsFacet.values"
                              "&finder=findReqs;siteNumber=CX_1001,facetsList=LOCATIONS,limit=5,keyword=%22data%22,"
                              "sortBy=POSTING_DATES_DESC,offset=0"), 12000)
# Amex on Oracle (egug.fa.us2). Try common site numbers.
for site in ("CX_1", "CX_1001", "CX_2", "CX_3"):
    res[f"amex_orc_{site}"] = clip(req("GET", "https://egug.fa.us2.oraclecloud.com" + ORC +
                                       f"?onlyData=true&finder=findReqs;siteNumber={site},keyword=%22data%22,limit=5,offset=0"), 2500)
    time.sleep(0.5)
# Amex careers page: find siteNumber in HTML
page = req("GET", "https://www.americanexpress.com/en-us/careers/")
body = page.get("body", "")
res["amex_page_hits"] = sorted(set(re.findall(r"egug\.fa\.us2\.oraclecloud\.com[^\"' <>]{0,160}", body)))[:20]
res["amex_page_eightfold"] = sorted(set(re.findall(r"aexp\.eightfold\.ai[^\"' <>]{0,160}", body)))[:20]
# Eightfold PCSX for aexp / starbucks / microsoft paging
res["amex_pcsx"] = clip(req("GET", "https://aexp.eightfold.ai/api/pcsx/search?domain=aexp.com&query=data&location=India&start=0"))
res["starbucks_pcsx"] = clip(req("GET", "https://starbucks.eightfold.ai/api/pcsx/search?domain=starbucks.com&query=data&location=India&start=0"))
res["starbucks_pcsx2"] = clip(req("GET", "https://careers.starbucks.com/api/pcsx/search?domain=starbucks.com&query=data&location=India&start=0"))
res["ms_pcsx_p2"] = clip(req("GET", "https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=data%20engineer&location=India&start=10"), 6000)
res["ms_position"] = clip(req("GET", "https://apply.careers.microsoft.com/api/pcsx/position_details?position_id=1970393556944049&domain=microsoft.com&hl=en"), 3000)
# Walmart: look for search API in the results page
w = req("GET", "https://careers.walmart.com/results?q=data%20engineer&page=1&sort=rank&jobCountry=IND")
wb = w.get("body", "")
res["walmart_results"] = {"status": w.get("status"), "final": w.get("final"), "len": len(wb),
                          "api_hits": sorted(set(re.findall(r"[\"'](/?api/[^\"']{3,120}|https://[\w.-]*walmart[\w.-]*/[^\"']*api[^\"']{0,100})[\"']", wb)))[:40],
                          "R_ids": len(re.findall(r"R-\d{6,}", wb)), "next": "__NEXT_DATA__" in wb, "head": wb[:1500]}
for u in ("https://careers.walmart.com/api/search?q=data%20engineer&country=IND",
          "https://careers.walmart.com/us/en/api/jobs?q=data%20engineer&country=India",
          "https://careers.walmart.com/us/en/results?searchQuery=data%20engineer&location=India"):
    res["walmart_try:" + u] = clip(req("GET", u), 2500)
# Google: structure of embedded data
g = req("GET", "https://www.google.com/about/careers/applications/jobs/results/?q=%22data%20engineer%22&location=India")
gb = g.get("body", "")
m = re.search(r"AF_initDataCallback\(\{key: 'ds:1'.*?data:(\[.*?\]), sideChannel", gb, re.S)
res["google"] = {"status": g.get("status"), "ds1": (m.group(1)[:6000] if m else None),
                 "keys": re.findall(r"AF_initDataCallback\(\{key: '([\w:]+)'", gb)[:10]}
# Tesco Avature feed and search page structure
res["tesco_feed"] = clip(req("GET", "https://careers.tesco.com/en_GB/careers/SearchJobs/feed/?524=%5B4%5D&keyword=data"), 5000)
tp = req("GET", "https://careers.tesco.com/en_GB/careers/SearchJobs/data?listFilterMode=1&jobRecordsPerPage=50")
tb = tp.get("body", "")
res["tesco_search"] = {"status": tp.get("status"), "links": sorted(set(re.findall(r"/careers/JobDetail/[\w-]+/\d+", tb)))[:20],
                       "india": len(re.findall(r"Bengaluru|India", tb)),
                       "snip": re.findall(r"article[^>]*>.{0,600}", tb, re.S)[:2]}
# Fidelity Workday: India filtered search
res["fidelity_wd"] = clip(req("POST", "https://fmr.wd1.myworkdayjobs.com/wday/cxs/fmr/FidelityCareers/jobs",
                              json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "data India"},
                              headers={"Content-Type": "application/json", "Accept": "application/json"}), 3000)
# Goldman: India results
res["goldman_india"] = clip(req("POST", "https://api-higher.gs.com/gateway/api/v1/graphql",
                                json={"operationName": "GetRoles", "variables": {"searchQueryInput": {
                                    "page": {"pageSize": 20, "pageNumber": 0}, "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                                    "filters": [{"filterCategoryType": "LOCATION", "filters": [{"filter": "India", "subFilters": []}]}],
                                    "experiences": ["PROFESSIONAL", "EARLY_CAREER"], "searchTerm": "data"}},
                                    "query": "query GetRoles($searchQueryInput: RoleSearchQueryInput!) { roleSearch(searchQueryInput: $searchQueryInput) "
                                             "{ totalCount items { roleId jobTitle corporateTitle jobFunction descriptionHtml externalSource { sourceId } "
                                             "locations { city state country } } } }"},
                                headers={"Content-Type": "application/json", "Origin": "https://higher.gs.com"}), 4000)
# Amazon fields
a = req("GET", "https://www.amazon.jobs/en/search.json?base_query=data%20engineer&loc_query=India&country=IND&result_limit=2&offset=0")
try:
    j = json.loads(a["body"])["jobs"][0]
    res["amazon_fields"] = {k: (str(v)[:120]) for k, v in j.items()}
except Exception as e:  # noqa: BLE001
    res["amazon_fields"] = str(e)

text = json.dumps(res, indent=1, default=str)
# keep anything that looks like a key or token out of the repo (push protection rejects it)
text = re.sub(r"AIza[0-9A-Za-z_\\-]{20,}", "AIza<redacted>", text)
text = re.sub(r"(?i)(key|token|secret|csrf|nonce)([\"':= ]{1,6})[A-Za-z0-9._\\-]{16,}", r"\1\2<redacted>", text)
with open("tools/probe4.json", "w") as fh:
    fh.write(text)
print("ok", len(res))
