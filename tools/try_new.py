"""Run the new GCC sources once and report what they return. Writes tools/try_new.json."""
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")
import app  # noqa: E402
import companies  # noqa: E402
import sources  # noqa: E402

NEW_WD = {s for s, _, _ in companies.WORKDAY[companies.WORKDAY.index(('wf|1|WellsFargoJobs', 'Wells Fargo', [])):]}
tasks = []
for ats in ("Oracle", "Eightfold", "Amazon", "Google", "Goldman Sachs", "Avature"):
    fn, lst = sources.ATS[ats]
    tasks += [(ats, fn, *e) for e in lst]
tasks += [("Workday", sources.workday, s, n, t) for s, n, t in companies.WORKDAY if s in NEW_WD]
tasks += [("Greenhouse", sources.greenhouse, "smartsheet", "Smartsheet", []), ("Greenhouse", sources.greenhouse, "airbnb", "Airbnb", []),
          ("SmartRecruiters", sources.smartrecruiters, "Experian", "Experian", []), ("SmartRecruiters", sources.smartrecruiters, "HMGroup", "H&M", [])]


def run(t):
    ats, fn, slug, name, tags = t
    t0 = time.time()
    try:
        raws = fn(slug, name, tags)
        kept = [j for j in (app.normalize(r, ats) for r in raws) if j]
        return name, {"ok": True, "secs": round(time.time() - t0), "total": len(raws), "kept": len(kept),
                      "regions": sorted({j["region"] for j in kept}),
                      "sample": [(j["title"], j["location"], j["region"], j["role"], bool(j["posted"])) for j in kept[:6]],
                      "raw_sample": [(r.get("title"), r.get("location"), len(r.get("desc") or "")) for r in raws[:3]]}
    except Exception as e:  # noqa: BLE001
        return name, {"ok": False, "secs": round(time.time() - t0), "error": repr(e)[:300],
                      "trace": traceback.format_exc()[-1200:]}


with ThreadPoolExecutor(max_workers=8) as pool:
    res = dict(pool.map(run, tasks))
with open("tools/try_new.json", "w") as fh:
    json.dump(res, fh, indent=1)
for k, v in res.items():
    print(k, v.get("ok"), v.get("total"), v.get("kept"), v.get("secs"), v.get("error", ""))
