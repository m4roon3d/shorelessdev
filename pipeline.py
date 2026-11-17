"""Fetch every source, normalise and de-duplicate the listings. Used by build.py."""
import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import classify
import sources

MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "60"))


def _pay(raw, desc):
    t = classify.fmt_pay(raw.get("pay"))
    if not t and raw.get("pay_text") and len(raw["pay_text"]) <= 40 and any(c.isdigit() for c in raw["pay_text"]):
        t = raw["pay_text"].strip()
    return t or classify.pay_from_text(desc)


def normalize(raw, source):
    title = " ".join((raw.get("title") or "").split())
    body = raw.get("body") or ""
    desc = (raw.get("desc") or "")[:8000]
    stack = classify.stack_of(title, desc)
    vendor = "vendor" in (raw.get("tags") or [])
    role = classify.role_of(title, stack, vendor)
    if not role:
        return None

    loc = raw.get("location") or ""
    region = classify.region_of(loc, raw.get("remote"), raw.get("restrictions"))
    if source == "HN Who's Hiring" and region in ("Unclear", "Locked") and not classify.LOCKED.search(title):
        r2 = classify.region_of(body[:800], True)
        if r2 in ("India", "APAC", "Worldwide"):
            region = r2
    if region == "Unclear":
        region = classify.region_from_desc(desc) or region
    elif region == "Locked" and raw.get("remote") and not classify.LOCKED.search(loc):
        # A remote role listed under an office city. Trust the description only when it names India,
        # or says worldwide at a company known to be all-remote (company boilerplate often says "global").
        r = classify.region_from_desc(desc)
        if r == "India" or (r == "Worldwide" and "allremote" in (raw.get("tags") or [])):
            region = r
    if region is None:
        return None

    remote_flag = raw.get("remote")
    if remote_flag is None:
        remote_flag = bool(classify.REMOTE.search(loc)) or raw.get("restrictions") is not None
    if "allremote" in (raw.get("tags") or []):
        remote_flag = True
    posted = raw.get("posted")
    if posted and time.time() - posted > MAX_AGE_DAYS * 86400:
        return None

    url = raw.get("url") or ""
    jid = hashlib.sha1((url or f"{raw.get('company')}|{title}").encode()).hexdigest()[:12]
    supply = "supply" in (raw.get("tags") or []) or classify.is_supply(title, raw.get("company"), desc[:3000])
    if raw.get("restrictions"):
        loc = ", ".join(raw["restrictions"][:6])
    pay = _pay(raw, desc)
    return dict(
        id=jid, title=title[:200], company=(raw.get("company") or "").strip(), url=url,
        location=(loc or ("Worldwide" if region == "Worldwide" else ""))[:160],
        region=region, remote=bool(remote_flag), role=role, level=classify.level_of(title),
        supply=supply, posted=posted, source=source,
        pay=pay, pay_n=classify.pay_usd(raw.get("pay"), pay) if pay else 0, etype=(raw.get("etype") or "")[:20],
        stack=sorted(stack, key=lambda k: (k in ("Python", "SQL"), list(classify.STACK).index(k)))[:6],
    )


def fetch_all():
    tasks = []
    for ats, (fn, lst) in sources.ATS.items():
        for slug, name, tags in lst:
            tasks.append((f"{ats}:{slug}", name, ats, lambda fn=fn, s=slug, n=name, t=tags: fn(s, n, t)))
    for name, fn in sources.FEEDS.items():
        tasks.append((name, name, name, fn))

    jobs, report = {}, []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = {pool.submit(t[3]): t for t in tasks}
        for f in as_completed(futs):
            key, name, src, _ = futs[f]
            try:
                raws = f.result()
                kept = 0
                for raw in raws:
                    j = normalize(raw, src)
                    if j and j["id"] not in jobs:
                        jobs[j["id"]] = j
                        kept += 1
                report.append(dict(key=key, name=name, ok=True, total=len(raws), kept=kept))
            except Exception as e:  # noqa: BLE001
                status = getattr(getattr(e, "response", None), "status_code", None)
                report.append(dict(key=key, name=name, ok=False, error=f"{status or type(e).__name__}"))
    # de-duplicate same company+title across sources (keep India-friendliest, newest)
    best = {}
    for j in jobs.values():
        k = (j["company"].lower(), j["title"].lower())
        cur = best.get(k)
        if not cur or (classify.REGION_ORDER[j["region"]], -(j["posted"] or 0)) < (
            classify.REGION_ORDER[cur["region"]], -(cur["posted"] or 0)
        ):
            best[k] = j
    out = sorted(best.values(), key=lambda j: -(j["posted"] or 0))
    report.sort(key=lambda r: (r["ok"], r["key"]))
    return out, report
