"""Fetch every source once and write static/jobs.json for the static site."""
import json
import os
import sys
import time

if os.environ.get("RENDER"):
    # The site host only serves the file the scheduled GitHub job committed; fetching again here
    # doubles the load on the job boards and gets the feed rate-limited.
    print("Using committed static/jobs.json")
    sys.exit(0)

import pipeline  # noqa: E402
import sources  # noqa: E402

# Workday sites run in their own daily job (build_workday.py); merge its last result here.
sources.ATS.pop("Workday", None)

t0 = time.time()
jobs, report = pipeline.fetch_all()
now = int(time.time())

try:
    with open("static/workday.json") as fh:
        wd = json.load(fh)
except (OSError, ValueError):
    wd = {}
if now - wd.get("updated", 0) < 3 * 86400:
    ids = {j["id"] for j in jobs}
    jobs += [{k: v for k, v in j.items() if k != "fetched"} for j in wd.get("jobs", []) if j["id"] not in ids]
    report += wd.get("sources", [])

try:
    with open("static/jobs.json") as fh:
        old = json.load(fh)
except (OSError, ValueError):
    old = {}
prev = {j["id"]: j for j in old.get("jobs", [])}

# first_seen = when a job first appeared in this feed; last_seen = last refresh that returned it
for j in jobs:
    p = prev.get(j["id"])
    j["first_seen"] = (p or {}).get("first_seen") or (now if prev else (j.get("posted") or now))
    j["last_seen"] = now

# Job-board feeds are searched, not listed, and can come back short when rate-limited.
# Keep a job for up to 36 hours after it was last returned when its source is a searched feed, or when its
# company board failed this run (rate limit, outage). A board that answered is authoritative: its closed jobs go.
have = {j["id"] for j in jobs}
failed = {(r["key"].split(":")[0], r["name"]) for r in report if not r["ok"]}
kept = 0
for j in prev.values():
    carry = j.get("source") in sources.FEEDS or (j.get("source"), j.get("company")) in failed
    if j["id"] not in have and carry and now - (j.get("last_seen") or old.get("updated") or 0) < 36 * 3600:
        j.setdefault("last_seen", old.get("updated") or now)
        jobs.append(j)
        kept += 1
jobs.sort(key=lambda j: -(j.get("posted") or 0))

out = {"jobs": jobs, "sources": report, "updated": now}
os.makedirs("static", exist_ok=True)
with open("static/jobs.json", "w") as fh:
    json.dump(out, fh, separators=(",", ":"))
bad = [r["key"] for r in report if not r["ok"]]
print(f"{len(jobs)} jobs ({kept} carried over), {len(report) - len(bad)}/{len(report)} sources ok, {time.time() - t0:.0f}s")
