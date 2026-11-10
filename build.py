"""Fetch every source once and write static/jobs.json for the static site."""
import json
import os
import time

os.environ["SHORELESS_BUILD"] = "1"
import app  # noqa: E402

t0 = time.time()
jobs, report = app.fetch_all()
out = {"jobs": jobs, "sources": report, "updated": int(time.time())}
os.makedirs("static", exist_ok=True)
with open("static/jobs.json", "w") as fh:
    json.dump(out, fh, separators=(",", ":"))
bad = [r["key"] for r in report if not r["ok"]]
print(f"{len(jobs)} jobs, {len(report) - len(bad)}/{len(report)} sources ok, {time.time() - t0:.0f}s")
