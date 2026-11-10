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


# ---------- company boards (ATS) ----------

def greenhouse(slug, name, tags):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"}).json()
    out = []
    for j in data.get("jobs", []):
        out.append(dict(
            title=j.get("title"), company=name, url=j.get("absolute_url"),
            location=(j.get("location") or {}).get("name", ""), remote=None, restrictions=None,
            posted=_iso(j.get("first_published") or j.get("updated_at")), tags=tags,
            desc=_strip(html.unescape(j.get("content") or "")),
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
        ))
    return out


def ashby(slug, name, tags):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").json()
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
            desc=j.get("descriptionPlain") or _strip(j.get("descriptionHtml")),
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


ATS = {
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
            ))
        if len(jobs) < 20:
            break
        time.sleep(0.3)
    for q in ("data engineer", "analytics engineer", "data architect", "data analyst", "etl", "snowflake"):
        try:
            data = _get("https://himalayas.app/jobs/api/search", params={"q": q, "limit": 20}).json()
        except requests.RequestException:
            continue
        for j in data.get("jobs", []):
            out.append(dict(
                title=j.get("title"), company=j.get("companyName"),
                url=j.get("applicationLink") or j.get("guid"), location="", remote=True,
                restrictions=j.get("locationRestrictions") or [],
                posted=int(j["pubDate"]) if isinstance(j.get("pubDate"), (int, float)) else _iso(j.get("pubDate")),
                tags=[], desc=_strip(j.get("description") or j.get("excerpt")),
            ))
        time.sleep(0.3)
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


FEEDS = {
    "HN Who's Hiring": hackernews,
    "Remotive": remotive,
    "RemoteOK": remoteok,
    "Himalayas": himalayas,
    "Jobicy": jobicy,
    "We Work Remotely": weworkremotely,
}
