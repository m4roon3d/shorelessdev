import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, jsonify, send_from_directory

import classify
import sources

REFRESH_EVERY = int(os.environ.get("REFRESH_HOURS", "6")) * 3600
MANUAL_MIN_GAP = 30 * 60
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "60"))
CACHE_FILE = os.environ.get("CACHE_FILE", "/tmp/shoreless_cache.json")

app = Flask(__name__, static_folder="static")

state = {"jobs": [], "sources": [], "updated": None, "refreshing": False, "started": None}
lock = threading.Lock()


def normalize(raw, source):
    title = (raw.get("title") or "").strip()
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
    return dict(
        id=jid, title=title[:200], company=(raw.get("company") or "").strip(), url=url,
        location=(loc or ("Worldwide" if region == "Worldwide" else ""))[:160],
        region=region, remote=bool(remote_flag), role=role, level=classify.level_of(title),
        supply=supply, posted=posted, source=source,
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


def refresh():
    with lock:
        if state["refreshing"]:
            return
        state["refreshing"] = True
        state["started"] = time.time()
    try:
        jobs, report = fetch_all()
        with lock:
            state.update(jobs=jobs, sources=report, updated=int(time.time()))
        bad = [f"{r['key']}={r['error']}" for r in report if not r["ok"]]
        by_region = {}
        for j in jobs:
            by_region[j["region"]] = by_region.get(j["region"], 0) + 1
        print(f"[refresh] {len(jobs)} jobs in {time.time() - state['started']:.0f}s; "
              f"{len(report) - len(bad)}/{len(report)} sources ok; regions={by_region}", flush=True)
        print(f"[refresh] failed: {', '.join(sorted(bad))}", flush=True)
        try:
            with open(CACHE_FILE, "w") as fh:
                json.dump({k: state[k] for k in ("jobs", "sources", "updated")}, fh)
        except OSError:
            pass
    finally:
        state["refreshing"] = False


def scheduler():
    while True:
        if not state["updated"] or time.time() - state["updated"] > REFRESH_EVERY:
            refresh()
        time.sleep(300)


def boot():
    try:
        with open(CACHE_FILE) as fh:
            state.update(json.load(fh))
    except (OSError, ValueError):
        pass
    threading.Thread(target=scheduler, daemon=True).start()


if not os.environ.get("SHORELESS_BUILD"):
    boot()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/jobs")
def api_jobs():
    return jsonify(
        jobs=state["jobs"], updated=state["updated"], refreshing=state["refreshing"],
        sources_ok=sum(1 for s in state["sources"] if s["ok"]), sources_total=len(state["sources"]),
    )


@app.get("/api/sources")
def api_sources():
    return jsonify(sources=state["sources"], updated=state["updated"])


@app.post("/api/refresh")
def api_refresh():
    if state["updated"] and time.time() - state["updated"] < MANUAL_MIN_GAP:
        return jsonify(ok=False, message="Refreshed less than 30 minutes ago."), 429
    threading.Thread(target=refresh, daemon=True).start()
    return jsonify(ok=True)


@app.get("/healthz")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8000)))
