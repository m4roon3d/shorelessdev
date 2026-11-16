"""Fetchers. Each returns a list of raw job dicts:
{title, company, url, location, remote(bool|None), restrictions(list|None), posted(epoch s|None), source, tags, extra}
"""
import html
import re
import time
from datetime import datetime, timezone

import requests

import companies

UA = {"User-Agent": "shoreless.dev/1.0 (personal job search tool)"}
TIMEOUT = 20


def _get(url, **kw):
    r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def _req(method, url, waits=(4, 12, 30), **kw):
    """requests call that waits and retries when the site rate-limits (429/503)."""
    kw.setdefault("timeout", TIMEOUT)
    for i, wait in enumerate((0,) + tuple(waits)):
        time.sleep(wait)
        r = requests.request(method, url, **kw)
        if r.status_code not in (429, 503) or i == len(waits):
            r.raise_for_status()
            return r
    return r


def _iso(s):
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return None


def _strip(h):
    return html.unescape(re.sub(r"<[^>]+>", " ", h or "")).strip()


def _num(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _rng(lo, hi, cur, per="yr"):
    lo, hi = _num(lo), _num(hi)
    if not lo and not hi:
        return None
    return {"min": lo or hi, "max": hi or lo, "cur": (cur or "USD").upper(), "per": per}


def _gh_pay(j):
    r = j.get("pay_input_ranges") or []
    if not r:
        return None
    return _rng((r[0].get("min_cents") or 0) / 100, (r[0].get("max_cents") or 0) / 100, r[0].get("currency_type"))


def _lever_pay(j):
    sr = j.get("salaryRange") or {}
    iv = (sr.get("interval") or "").lower()
    return _rng(sr.get("min"), sr.get("max"), sr.get("currency"), "hr" if "hour" in iv else "mo" if "month" in iv else "yr")


def _ashby_pay(j):
    c = j.get("compensation") or {}
    t = c.get("scrapeableCompensationSalarySummary") or c.get("compensationTierSummary")
    return {"text": t.split(" \u2022 ")[0].strip()[:40]} if t else None


# ---------- company boards (ATS) ----------

def greenhouse(slug, name, tags):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true", "pay_transparency": "true"}).json()
    out = []
    for j in data.get("jobs", []):
        out.append(dict(
            title=j.get("title"), company=name, url=j.get("absolute_url"),
            location=(j.get("location") or {}).get("name", ""), remote=None, restrictions=None,
            posted=_iso(j.get("first_published") or j.get("updated_at")), tags=tags,
            desc=_strip(html.unescape(j.get("content") or "")), pay=_gh_pay(j),
        ))
    return out


def lever(slug, name, tags):
    data = _get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}).json()
    out = []
    for j in data:
        cat = j.get("categories") or {}
        locs = [cat.get("location") or ""] + (cat.get("allLocations") or [])
        loc = ", ".join(dict.fromkeys(l for l in locs if l))
        wt = (j.get("workplaceType") or "").lower()
        out.append(dict(
            title=j.get("text"), company=name, url=j.get("hostedUrl"), location=loc,
            remote=True if wt == "remote" else None, restrictions=None,
            posted=int(j["createdAt"] / 1000) if j.get("createdAt") else None, tags=tags,
            desc=(j.get("descriptionPlain") or "") + " " + " ".join(_strip(l.get("content", "")) for l in j.get("lists") or []),
            pay=_lever_pay(j),
        ))
    return out


def ashby(slug, name, tags):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", params={"includeCompensation": "true"}).json()
    out = []
    for j in data.get("jobs", []):
        locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        loc = ", ".join(dict.fromkeys(l for l in locs if l))
        remote = j.get("isRemote")
        if (j.get("workplaceType") or "").lower() == "remote":
            remote = True
        out.append(dict(
            title=j.get("title"), company=name, url=j.get("jobUrl"), location=loc,
            remote=remote, restrictions=None, posted=_iso(j.get("publishedAt")), tags=tags,
            desc=j.get("descriptionPlain") or _strip(j.get("descriptionHtml")), pay=_ashby_pay(j),
        ))
    return out


def smartrecruiters(slug, name, tags):
    out, offset = [], 0
    while offset < 500:
        data = _get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                    params={"limit": 100, "offset": offset}).json()
        items = data.get("content", [])
        for j in items:
            loc = j.get("location") or {}
            out.append(dict(
                title=j.get("name"), company=name,
                url=f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                location=loc.get("fullLocation") or ", ".join(filter(None, [loc.get("city"), loc.get("country")])),
                remote=bool(loc.get("remote")) or None, restrictions=None,
                posted=_iso(j.get("releasedDate")), tags=tags,
            ))
        if len(items) < 100:
            break
        offset += 100
    return out


def workable(slug, name, tags):
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}").json()
    out = []
    for j in data.get("jobs", []):
        loc = ", ".join(filter(None, [j.get("city"), j.get("state"), j.get("country")]))
        out.append(dict(
            title=j.get("title"), company=name, url=j.get("url") or j.get("application_url"),
            location=loc, remote=True if j.get("telecommuting") else None, restrictions=None,
            posted=_iso(j.get("published_on") or j.get("created_at")), tags=tags,
            desc=_strip(j.get("description")),
        ))
    return out


def recruitee(slug, name, tags):
    data = _get(f"https://{slug}.recruitee.com/api/offers/").json()
    out = []
    for j in data.get("offers", []):
        loc = j.get("location") or ", ".join(filter(None, [j.get("city"), j.get("country")]))
        out.append(dict(
            title=j.get("title"), company=name, url=j.get("careers_url"), location=loc,
            remote=True if j.get("remote") else None, restrictions=None,
            posted=_iso((j.get("published_at") or "").replace(" UTC", "+00:00").replace(" ", "T", 1)), tags=tags,
            desc=_strip(j.get("description")) + " " + _strip(j.get("requirements")),
        ))
    return out


def personio(slug, name, tags):
    r = None
    for tld in ("de", "com"):
        r = requests.get(f"https://{slug}.jobs.personio.{tld}/xml", headers=UA, timeout=TIMEOUT)
        if r.status_code == 200 and "<position" in r.text:
            break
    r.raise_for_status()
    out = []
    for p in re.findall(r"<position>(.*?)</position>", r.text, re.S):
        def tag(t):
            m = re.search(rf"<{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", p, re.S)
            return html.unescape(m.group(1)).strip() if m else ""
        offices = ", ".join(dict.fromkeys([tag("office")] + re.findall(r"<additionalOffice>(.*?)</additionalOffice>", p)))
        desc = " ".join(_strip(html.unescape(v)) for v in re.findall(r"<value>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</value>", p, re.S))
        out.append(dict(
            title=tag("name"), company=name, url=f"https://{slug}.jobs.personio.{tld}/job/{tag('id')}",
            location=offices.strip(", "), remote=True if re.search(r"remote", offices, re.I) else None, restrictions=None,
            posted=_iso(tag("createdAt")), tags=tags, desc=desc, etype=tag("employmentType").replace("permanent", "Full Time"),
        ))
    return out


def teamtailor(slug, name, tags):
    xml = _get(f"https://{slug}.teamtailor.com/jobs.rss").text
    out = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def tag(t):
            m = re.search(rf"<{t}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", item, re.S)
            return html.unescape(m.group(1)).strip() if m else ""
        locs = [html.unescape(x) for x in re.findall(r"<tt:(?:city|country|name)>(.*?)</tt:(?:city|country|name)>", item)]
        remote_status = tag("tt:remoteStatus") or tag("remoteStatus")
        desc = _strip(tag("description"))
        try:
            posted = int(datetime.strptime(tag("pubDate"), "%a, %d %b %Y %H:%M:%S %z").timestamp())
        except ValueError:
            posted = None
        out.append(dict(
            title=tag("title"), company=name, url=tag("link"), location=", ".join(dict.fromkeys(locs)),
            remote=True if re.search(r"remote|fully|temporary", remote_status, re.I) or re.search(r"\bremote\b", tag("title"), re.I) else None,
            restrictions=None, posted=posted, tags=tags, desc=desc,
        ))
    return out


_WD_AGO = re.compile(r"(\d+)\+? Days? Ago", re.I)
WD_QUERIES = ("data engineer", "data architect", "data analyst", "analytics engineer", "etl", "business intelligence", "big data")


def _wd_posted(text):
    t = (text or "").lower()
    day = 86400
    if "today" in t:
        return int(time.time())
    if "yesterday" in t:
        return int(time.time()) - day
    m = _WD_AGO.search(t)
    return int(time.time()) - int(m.group(1)) * day if m else None


def workday(slug, name, tags):
    """slug is "tenant|wd number|site". Searches data roles, keeps those in India or remote, then reads each posting."""
    import classify  # local import: classify has no dependency on sources
    tenant, wd, site = slug.split("|")
    base = f"https://{tenant}.wd{wd}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}"
    hdr = {**UA, "Accept": "application/json", "Content-Type": "application/json"}
    seen, picks = set(), []
    for q in WD_QUERIES:
        for offset in (0, 20, 40):
            r = _req("POST", f"{api}/jobs", json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": q},
                     headers=hdr)
            posts = r.json().get("jobPostings") or []
            for p in posts:
                path = p.get("externalPath")
                if not path or path in seen:
                    continue
                seen.add(path)
                loc = p.get("locationsText") or ""
                if not classify.role_of(p.get("title") or ""):
                    continue
                if not (classify.INDIA.search(loc) or classify.REMOTE.search(loc) or re.search(r"\d+ Locations", loc)):
                    continue
                picks.append(p)
            if len(posts) < 20:
                break
        time.sleep(0.3)
    out = []
    for p in picks[:60]:
        info = {}
        try:
            info = requests.get(f"{api}{p['externalPath']}", headers=hdr, timeout=TIMEOUT).json().get("jobPostingInfo") or {}
        except (requests.RequestException, ValueError):
            pass
        locs = [info.get("location") or p.get("locationsText") or ""] + list(info.get("additionalLocations") or [])
        loc = ", ".join(dict.fromkeys(l for l in locs if l))
        rt = (info.get("remoteType") or "").lower()
        out.append(dict(
            title=info.get("title") or p.get("title"), company=name,
            url=info.get("externalUrl") or f"{base}/{site}{p['externalPath']}", location=loc,
            remote=True if "remote" in rt or re.search(r"\bremote\b", loc, re.I) else None, restrictions=None,
            posted=_iso(info.get("startDate")) or _wd_posted(p.get("postedOn")), tags=tags,
            desc=_strip(info.get("jobDescription")), etype=info.get("timeType") or "",
        ))
        time.sleep(0.2)
    return out


# ---------- big-employer career sites (India tech centres / GCCs) ----------
# These are searched, not listed: we run the data-role queries, keep data titles, and (where the API is
# global) keep roles in India or remote. Descriptions are fetched for the picks only.

def _data_title(t):
    import classify
    return bool(classify.role_of(t or ""))


def _india_or_remote(loc):
    import classify
    return bool(classify.INDIA.search(loc or "") or classify.REMOTE.search(loc or ""))


ORC = "/hcmRestApi/resources/latest/recruitingCEJobRequisitions"


def oracle(slug, name, tags):
    """Oracle Recruiting Cloud. slug is "host|siteNumber", e.g. "jpmc.fa.oraclecloud.com|CX_1001"."""
    host, site = slug.split("|")
    base = f"https://{host}"
    hdr = {**UA, "Accept": "application/json"}

    def search(extra, limit=25, offset=0):
        finder = f"findReqs;siteNumber={site},limit={limit},offset={offset},sortBy=POSTING_DATES_DESC{extra}"
        r = _req("GET", f"{base}{ORC}", params={"onlyData": "true", "expand": "requisitionList.secondaryLocations",
                                                "finder": finder}, headers=hdr)
        items = r.json().get("items") or [{}]
        return items[0]

    # find the India location id from the location facet
    facet = search(",facetsList=LOCATIONS", limit=1)
    india = next((f["Id"] for f in facet.get("locationsFacet") or [] if (f.get("Name") or "").strip().lower() == "india"), None)
    loc_q = f",locationId={india}" if india else ""
    seen, picks = set(), []
    for q in WD_QUERIES:
        for offset in (0, 25, 50):
            res = search(f',keyword="{q}"{loc_q}', offset=offset)
            reqs = res.get("requisitionList") or []
            for p in reqs:
                if p.get("Id") in seen or not _data_title(p.get("Title")):
                    continue
                seen.add(p.get("Id"))
                locs = [p.get("PrimaryLocation") or ""] + [s.get("Name", "") for s in p.get("secondaryLocations") or []]
                p["_loc"] = ", ".join(dict.fromkeys(l for l in locs if l))
                if india or _india_or_remote(p["_loc"]):
                    picks.append(p)
            if len(reqs) < 25:
                break
        time.sleep(0.3)
    out = []
    for p in picks[:80]:
        desc = p.get("ShortDescriptionStr") or ""
        try:
            d = requests.get(f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails",
                             params={"expand": "all", "onlyData": "true",
                                     "finder": f'ById;Id="{p["Id"]}",siteNumber={site}'},
                             headers=hdr, timeout=TIMEOUT).json().get("items") or [{}]
            d = d[0]
            desc = " ".join(_strip(d.get(k)) for k in ("ExternalDescriptionStr", "ExternalResponsibilitiesStr",
                                                         "ExternalQualificationsStr") if d.get(k)) or desc
        except (requests.RequestException, ValueError):
            pass
        wt = (p.get("WorkplaceType") or p.get("WorkplaceTypeCode") or "").lower()
        out.append(dict(
            title=p.get("Title"), company=name, url=f"{base}/hcmUI/CandidateExperience/en/sites/{site}/job/{p['Id']}",
            location=p["_loc"], remote=True if "remote" in wt else None, restrictions=None,
            posted=_iso((p.get("PostedDate") or "") + "T00:00:00") if p.get("PostedDate") else None, tags=tags,
            desc=desc,
        ))
        time.sleep(0.15)
    return out


def eightfold(slug, name, tags):
    """Eightfold career sites (PCSX API). slug is "host|domain", e.g. "apply.careers.microsoft.com|microsoft.com"."""
    host, domain = slug.split("|")
    base = f"https://{host}"
    hdr = {**UA, "Accept": "application/json"}
    seen, picks = set(), []
    for q in WD_QUERIES:
        for start in (0, 10, 20, 30, 40):
            try:
                r = _req("GET", f"{base}/api/pcsx/search", params={"domain": domain, "query": q, "location": "India", "start": start},
                         headers=hdr, waits=(8, 20, 45))
            except requests.HTTPError:
                if picks:
                    break  # still rate-limited: keep what we have
                raise
            pos = (r.json().get("data") or {}).get("positions") or []
            time.sleep(1.2)
            for p in pos:
                if p.get("id") in seen or not _data_title(p.get("name")):
                    continue
                seen.add(p.get("id"))
                loc = ", ".join(p.get("locations") or [])
                if _india_or_remote(loc) or p.get("workLocationOption") == "remote":
                    picks.append(p)
            if len(pos) < 10:
                break
        time.sleep(0.3)
    out = []
    for p in picks[:80]:
        desc = ""
        try:
            d = _req("GET", f"{base}/api/pcsx/position_details", params={"position_id": p["id"], "domain": domain, "hl": "en"},
                     headers=hdr, waits=(8, 20)).json().get("data") or {}
            desc = _strip(d.get("jobDescription"))
        except (requests.RequestException, ValueError):
            pass
        time.sleep(0.8)
        out.append(dict(
            title=p.get("name"), company=name, url=f"{base}{p.get('positionUrl') or ''}",
            location=", ".join(p.get("locations") or []),
            remote=True if p.get("workLocationOption") == "remote" else None, restrictions=None,
            posted=int(p["postedTs"]) if p.get("postedTs") else None, tags=tags, desc=desc,
        ))
        time.sleep(0.15)
    return out


def amazon(slug, name, tags):
    """amazon.jobs search API, India only. slug is the country code (IND)."""
    seen, out = set(), []
    for q in WD_QUERIES:
        for offset in (0, 100):
            data = _get("https://www.amazon.jobs/en/search.json",
                        params={"base_query": q, "country": slug, "result_limit": 100, "offset": offset,
                                "sort": "recent"}).json()
            jobs = data.get("jobs") or []
            for j in jobs:
                if j.get("id") in seen or not _data_title(j.get("title")):
                    continue
                seen.add(j.get("id"))
                try:
                    posted = int(datetime.strptime(j.get("posted_date") or "", "%B %d, %Y").replace(tzinfo=timezone.utc).timestamp())
                except ValueError:
                    posted = None
                out.append(dict(
                    title=j.get("title"), company=name, url=f"https://www.amazon.jobs{j.get('job_path') or ''}",
                    location=j.get("normalized_location") or j.get("location") or "", remote=None, restrictions=None,
                    posted=posted, tags=tags, etype=(j.get("job_schedule_type") or "").replace("-", " ").title(),
                    desc=" ".join(_strip(j.get(k)) for k in ("description", "basic_qualifications", "preferred_qualifications")),
                ))
            if len(jobs) < 100:
                break
        time.sleep(0.5)
    return out


_G_DATA = re.compile(r"AF_initDataCallback\(\{key: 'ds:1', hash: '\d+', data:(\[.*?\]), sideChannel", re.S)


def _walk(x):
    if isinstance(x, list):
        for y in x:
            yield from _walk(y)
    else:
        yield x


def google(slug, name, tags):
    """Google careers. The results page embeds the jobs as a JSON array; slug is the location filter (India)."""
    import json
    seen, out = set(), []
    for q in WD_QUERIES:
        for page in (1, 2, 3):
            html_ = _get("https://www.google.com/about/careers/applications/jobs/results/",
                         params={"q": f'"{q}"', "location": slug, "page": page}).text
            m = _G_DATA.search(html_)
            if not m:
                break
            try:
                jobs = (json.loads(m.group(1)) or [[]])[0] or []
            except ValueError:
                break
            for j in jobs:
                if not isinstance(j, list) or len(j) < 3:
                    continue
                jid, title = j[0], j[1]
                if jid in seen or not _data_title(title):
                    continue
                seen.add(jid)
                strings = [s for s in _walk(j[3:]) if isinstance(s, str)]
                locs = [s for s in strings if len(s) < 60 and re.search(r",\s*[A-Z][a-z]+$", s) and "<" not in s and not re.search(r"\d", s)]
                ts = next((p[0] for p in (k for k in j if isinstance(k, list)) if len(p) == 2
                           and all(isinstance(v, int) for v in p) and 1.5e9 < p[0] < 2.5e9), None)
                slug_t = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                out.append(dict(
                    title=title, company=name, url=f"https://www.google.com/about/careers/applications/jobs/results/{jid}-{slug_t}",
                    location=", ".join(dict.fromkeys(locs[:6])) or slug, remote=None, restrictions=None, posted=ts,
                    tags=tags, desc=" ".join(_strip(s) for s in strings if "<" in s)[:8000],
                ))
            if len(jobs) < 20:
                break
            time.sleep(0.8)
    return out


GS_QUERY = ("query GetRoles($searchQueryInput: RoleSearchQueryInput!) { roleSearch(searchQueryInput: $searchQueryInput) "
            "{ totalCount items { roleId jobTitle corporateTitle descriptionHtml externalSource { sourceId } "
            "locations { city state country } } } }")


def goldman(slug, name, tags):
    """Goldman Sachs (higher.gs.com GraphQL), filtered to one country (slug)."""
    seen, out = set(), []
    hdr = {**UA, "Content-Type": "application/json", "Origin": "https://higher.gs.com"}
    for q in WD_QUERIES:
        for page in range(4):
            body = {"operationName": "GetRoles", "query": GS_QUERY, "variables": {"searchQueryInput": {
                "page": {"pageSize": 50, "pageNumber": page}, "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                "filters": [{"filterCategoryType": "LOCATION", "filters": [{"filter": slug, "subFilters": []}]}],
                "experiences": ["PROFESSIONAL", "EARLY_CAREER"], "searchTerm": q}}}
            r = _req("POST", "https://api-higher.gs.com/gateway/api/v1/graphql", json=body, headers=hdr)
            items = ((r.json().get("data") or {}).get("roleSearch") or {}).get("items") or []
            for j in items:
                sid = (j.get("externalSource") or {}).get("sourceId") or j.get("roleId")
                if sid in seen or not _data_title(j.get("jobTitle")):
                    continue
                seen.add(sid)
                loc = "; ".join(", ".join(filter(None, [l.get("city"), l.get("country")])) for l in j.get("locations") or [])
                out.append(dict(
                    title=j.get("jobTitle"), company=name, url=f"https://higher.gs.com/roles/{sid}", location=loc,
                    remote=None, restrictions=None, posted=None, tags=tags, desc=_strip(j.get("descriptionHtml")),
                ))
            if len(items) < 50:
                break
        time.sleep(0.4)
    return out


def avature(slug, name, tags):
    """Avature career sites (e.g. Tesco). slug is "host|locale path", e.g. "careers.tesco.com|en_GB/careers".
    Keeps roles whose legal entity or location is in India."""
    import classify
    host, path = slug.split("|")
    seen, out = set(), []
    for q in WD_QUERIES:
        for offset in (0, 50, 100):
            page = _get(f"https://{host}/{path}/SearchJobs/{requests.utils.quote(q)}",
                        params={"listFilterMode": 1, "jobRecordsPerPage": 50, "jobOffset": offset}).text
            arts = page.split('class="article article--result')[1:]
            for a in arts:
                m = re.search(r'href="(https://[^"]+/JobDetail/[^"]+)"[^>]*>\s*(.*?)\s*</a>', a, re.S)
                if not m:
                    continue
                url, title = m.group(1), html.unescape(_strip(m.group(2)))
                ent = _strip((re.search(r'list-item-legalEntity">(.*?)<', a) or [None, ""])[1])
                loc = _strip((re.search(r'list-item-location">(.*?)<', a) or [None, ""])[1])
                if url in seen or not _data_title(title):
                    continue
                seen.add(url)
                if not (classify.INDIA.search(ent) or classify.INDIA.search(loc) or classify.REMOTE.search(loc)):
                    continue
                desc = ""
                try:
                    desc = _strip(re.sub(r"(?s)<(script|style).*?</\1>", " ", _get(url).text))[:6000]
                except requests.RequestException:
                    pass
                out.append(dict(
                    title=title, company=name, url=url, location=", ".join(filter(None, [loc, "India" if "india" in ent.lower() else ""])),
                    remote=None, restrictions=None, posted=None, tags=tags, desc=desc,
                ))
            if len(arts) < 50:
                break
        time.sleep(0.4)
    return out


ATS = {
    "Oracle": (oracle, getattr(companies, "ORACLE", [])),
    "Eightfold": (eightfold, getattr(companies, "EIGHTFOLD", [])),
    "Amazon": (amazon, getattr(companies, "AMAZON", [])),
    "Google": (google, getattr(companies, "GOOGLE", [])),
    "Goldman Sachs": (goldman, getattr(companies, "GOLDMAN", [])),
    "Avature": (avature, getattr(companies, "AVATURE", [])),
    "Recruitee": (recruitee, getattr(companies, "RECRUITEE", [])),
    "Personio": (personio, getattr(companies, "PERSONIO", [])),
    "Teamtailor": (teamtailor, getattr(companies, "TEAMTAILOR", [])),
    "Workday": (workday, getattr(companies, "WORKDAY", [])),
    "Greenhouse": (greenhouse, companies.GREENHOUSE),
    "Lever": (lever, companies.LEVER),
    "Ashby": (ashby, companies.ASHBY),
    "SmartRecruiters": (smartrecruiters, companies.SMARTRECRUITERS),
    "Workable": (workable, companies.WORKABLE),
}


# ---------- remote job feeds ----------

def remotive():
    out = []
    for cat in ("data", "software-dev"):
        data = _get("https://remotive.com/api/remote-jobs", params={"category": cat}).json()
        for j in data.get("jobs", []):
            out.append(dict(
                title=j.get("title"), company=j.get("company_name"), url=j.get("url"),
                location=j.get("candidate_required_location") or "Worldwide", remote=True, restrictions=None,
                posted=_iso(j.get("publication_date")), tags=[], desc=_strip(j.get("description")),
                pay_text=j.get("salary"),
            ))
    return out


def remoteok():
    data = []
    for params in ({}, {"tag": "data"}, {"tag": "analytics"}):
        try:
            d = _get("https://remoteok.com/api", params=params).json()
            data += [j for j in d if "legal" not in j]
        except requests.RequestException:
            continue
        time.sleep(1)
    out = []
    for j in data:
        out.append(dict(
            title=j.get("position"), company=j.get("company"), url=j.get("url"),
            location=j.get("location") or "Worldwide", remote=True, restrictions=None,
            posted=int(j["epoch"]) if j.get("epoch") else _iso(j.get("date")), tags=[],
            desc=_strip(j.get("description")) + " " + " ".join(j.get("tags") or []),
            pay=_rng(j.get("salary_min"), j.get("salary_max"), "USD"),
        ))
    return out


def himalayas():
    out = []
    for page in range(10):
        data = _get("https://himalayas.app/jobs/api", params={"limit": 20, "offset": page * 20}).json()
        jobs = data.get("jobs", [])
        for j in jobs:
            out.append(dict(
                title=j.get("title"), company=j.get("companyName"),
                url=j.get("applicationLink") or j.get("guid"), location="", remote=True,
                restrictions=j.get("locationRestrictions") or [],
                posted=int(j["pubDate"]) if isinstance(j.get("pubDate"), (int, float)) else _iso(j.get("pubDate")),
                tags=[], desc=_strip(j.get("description") or j.get("excerpt")),
                pay=_rng(j.get("minSalary"), j.get("maxSalary"), j.get("currency") or j.get("salaryCurrency")),
                etype=j.get("employmentType"),
            ))
        if len(jobs) < 20:
            break
        time.sleep(0.3)
    queries = ("data engineer", "analytics engineer", "data architect", "data analyst", "etl", "snowflake",
               "databricks", "dbt", "bi developer", "power bi", "data platform", "informatica", "azure data",
               "big data", "data warehouse", "data integration", "spark", "airflow")
    searches = [{"q": q, "limit": 20, "page": p} for q in queries for p in (1, 2)]
    searches += [{"q": q, "limit": 20, "country": "India"} for q in queries]
    missed = 0
    for params in searches:
        data = None
        for wait in (0, 8, 20):  # back off when rate-limited instead of silently losing the search
            time.sleep(wait)
            try:
                data = _get("https://himalayas.app/jobs/api/search", params=params).json()
                break
            except (requests.RequestException, ValueError):
                continue
        if data is None:
            missed += 1
            continue
        for j in data.get("jobs", []):
            out.append(dict(
                title=j.get("title"), company=j.get("companyName"),
                url=j.get("applicationLink") or j.get("guid"), location="", remote=True,
                restrictions=j.get("locationRestrictions") or [],
                posted=int(j["pubDate"]) if isinstance(j.get("pubDate"), (int, float)) else _iso(j.get("pubDate")),
                tags=[], desc=_strip(j.get("description") or j.get("excerpt")),
                pay=_rng(j.get("minSalary"), j.get("maxSalary"), j.get("currency") or j.get("salaryCurrency")),
                etype=j.get("employmentType"),
            ))
        time.sleep(0.6)
    if missed:
        print(f"[himalayas] {missed} of {len(searches)} searches failed", flush=True)
    return out


def jobicy():
    out = []
    for params in ({"count": 100, "tag": "data engineer"}, {"count": 100, "tag": "data"}, {"count": 100, "tag": "analytics"},
                   {"count": 100, "tag": "etl"}, {"count": 100, "geo": "apac"}, {"count": 100, "geo": "india"}):
        try:
            data = _get("https://jobicy.com/api/v2/remote-jobs", params=params).json()
        except requests.HTTPError:
            continue
        for j in data.get("jobs", []):
            out.append(dict(
                title=_strip(j.get("jobTitle")), company=j.get("companyName"), url=j.get("url"),
                location=j.get("jobGeo") or "", remote=True, restrictions=None,
                posted=_iso(j.get("pubDate")), tags=[], desc=_strip(j.get("jobDescription") or j.get("jobExcerpt")),
                pay=_rng(j.get("annualSalaryMin"), j.get("annualSalaryMax"), j.get("salaryCurrency")),
            ))
    return out


def weworkremotely():
    out = []
    for cat in ("remote-programming-jobs", "remote-devops-sysadmin-jobs", "all-other-remote-jobs"):
        xml = _get(f"https://weworkremotely.com/categories/{cat}.rss").text
        for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
            def tag(t):
                m = re.search(rf"<{t}>(.*?)</{t}>", item, re.S)
                return html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))).strip() if m else ""
            title = tag("title")
            company, _, role = title.partition(": ")
            pub = tag("pubDate")
            try:
                posted = int(datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z").timestamp())
            except Exception:
                posted = None
            out.append(dict(
                title=role or title, company=company if role else "", url=tag("link"),
                location=tag("region") or "Anywhere", remote=True, restrictions=None, posted=posted, tags=[],
                desc=_strip(tag("description")),
            ))
    return out


def hackernews():
    hits = _get("https://hn.algolia.com/api/v1/search_by_date",
                params={"tags": "story,author_whoishiring", "hitsPerPage": 10}).json()["hits"]
    story = next((h for h in hits if "who is hiring" in (h.get("title") or "").lower()), None)
    if not story:
        return []
    item = _get(f"https://hn.algolia.com/api/v1/items/{story['objectID']}").json()
    out = []
    for c in item.get("children", []):
        raw = c.get("text") or ""
        if not raw:
            continue
        first = _strip(raw.split("<p>")[0])
        body = _strip(raw)
        if not re.search(r"remote", body, re.I):
            continue
        parts = [p.strip() for p in first.split("|")]
        company = parts[0][:60] if parts else ""
        out.append(dict(
            title=first[:200], company=company,
            url=f"https://news.ycombinator.com/item?id={c.get('id')}",
            location=first, remote=True, restrictions=None,
            posted=c.get("created_at_i"), tags=[], body=body[:4000], desc=body[:6000],
        ))
    return out


def workingnomads():
    data = _get("https://www.workingnomads.com/api/exposed_jobs/").json()
    out = []
    for j in data:
        out.append(dict(
            title=j.get("title"), company=j.get("company_name"), url=j.get("url"),
            location=j.get("location") or "Anywhere", remote=True, restrictions=None,
            posted=_iso(j.get("pub_date")), tags=[],
            desc=_strip(j.get("description")) + " " + (j.get("tags") or ""),
        ))
    return out


FEEDS = {
    "Working Nomads": workingnomads,
    "HN Who's Hiring": hackernews,
    "Remotive": remotive,
    "RemoteOK": remoteok,
    "Himalayas": himalayas,
    "Jobicy": jobicy,
    "We Work Remotely": weworkremotely,
}
