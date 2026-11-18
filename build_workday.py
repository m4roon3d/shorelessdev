"""Fetch the Workday career sites once, slowly, and write static/workday.json.

Workday rate-limits by IP across all its customers, so these sites run in their own daily job, one site at a
time, instead of inside the 6-hourly refresh. build.py merges the result into static/jobs.json.
"""
import json
import threading
import time

import pipeline
import sources

sources._WD_LANE = threading.Semaphore(1)
sources.ATS = {"Workday": sources.ATS["Workday"]}
sources.FEEDS = {}

t0 = time.time()
jobs, report = pipeline.fetch_all()
now = int(time.time())

try:
    with open("static/workday.json") as fh:
        old = json.load(fh)
except (OSError, ValueError):
    old = {}

# A site that failed this run keeps its jobs from the last good run for up to 3 days.
failed = {r["name"] for r in report if not r["ok"]}
have = {j["id"] for j in jobs}
kept = 0
for j in old.get("jobs", []):
    if j["id"] not in have and j.get("company") in failed and now - (j.get("fetched") or 0) < 3 * 86400:
        jobs.append(j)
        kept += 1
for j in jobs:
    j.setdefault("fetched", now)

with open("static/workday.json", "w") as fh:
    json.dump({"jobs": jobs, "sources": report, "updated": now}, fh, separators=(",", ":"))
bad = [r["key"] for r in report if not r["ok"]]
print(f"{len(jobs)} Workday jobs ({kept} carried over), {len(report) - len(bad)}/{len(report)} sites ok, {time.time() - t0:.0f}s")
