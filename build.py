"""Fetch every source once and write static/jobs.json for the static site."""
import json
import os
import time

os.environ["SHORELESS_BUILD"] = "1"
import app  # noqa: E402

t0 = time.time()
jobs, report = app.fetch_all()

# first_seen = when a job first appeared in this feed, carried over from the previous file
try:
    with open("static/jobs.json") as fh:
        prev = {j["id"]: j.get("first_seen") for j in json.load(fh).get("jobs", [])}
except (OSError, ValueError):
    prev = {}
now = int(time.time())
for j in jobs:
    j["first_seen"] = prev.get(j["id"]) or (now if prev and j["id"] not in prev else (j.get("posted") or now))
out = {"jobs": jobs, "sources": report, "updated": int(time.time())}
os.makedirs("static", exist_ok=True)
with open("static/jobs.json", "w") as fh:
    json.dump(out, fh, separators=(",", ":"))
bad = [r["key"] for r in report if not r["ok"]]
print(f"{len(jobs)} jobs, {len(report) - len(bad)}/{len(report)} sources ok, {time.time() - t0:.0f}s")
