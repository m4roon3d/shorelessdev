"""Find which hiring platform each candidate company uses. Writes tools/probe.json."""
import json
import re
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "shoreless.dev/1.0 (board probe)"}
DATA = re.compile(r"data|analytics|etl|bi engineer|business intelligence|warehouse", re.I)

CANDIDATES = """
blueyonder kinaxis e2open manh manhattanassociates descartes coupa locus locussh fareye shipsy delhivery shiprocket
pando pandoai gocomet freightify zencargo forto sennder wisetech wisetechglobal transporeon alpega parcellab shipium
optoro loopreturns turvo mastery masterylogistics arrive arrivelogistics greenscreens greenscreensai optimaldynamics
platformscience trimble relaypayments outrider einride cargoone xeneta vizion portcast windward gnosisfreight
overhaul tive roambee shipbob stord shippo easypost flexe deliverr veho bringg onfleet routific cogoport
spinnakersca plantensive clarkston clarkstonconsulting bristlecone 4sightsolutions jbhunt chrobinson echo
sigmoid tredence fractal fractalanalytics tigeranalytics latentview musigma quantiphi thoughtspot rudderstack
hasura postman browserstack chargebee clevertap moengage razorpay zeta innovaccer mindtickle whatfix druva
icertis uniphore sprinklr yellowai perfios kissflow zluri atomicwork rocketlane fyle springworks uplers
crossover proxify braintrust xteam x-team bairesdev epam globant nagarro publicissapient tigerdata lumenalta
automattic buffer close helpscout articulate invision duckduckgo mozilla wikimedia hashicorp sourcegraph netlify
calcom n8n mattermost sentry 1password clickup hubstaff safetywing chainlinklabs consensys ghost timescale redis
confluent snowplow snowplowanalytics metabase preset census segment mixpanel amplitude heap dbtlabs dbtlabsinc
dataiku alteryx sisu selectstar castordoc coalesce coalesceio paradime y42 keboola rivery estuary decodable
risingwave singlestore upsolver qlik domo gooddata exasol firebolt databento tecton featureform zenml
welocalize telus telusinternational turing mercor micro1 outlier scaleai invisible invisibletech crossing
canva atlassian wise revolut monzo n26 gojek grab shopee agoda booking deliveryhero glovo bolt wolt
""".split()
import sys
sys.path.insert(0, ".")
import companies  # noqa: E402
HAVE = {slug.lower() for lst in (companies.GREENHOUSE, companies.LEVER, companies.ASHBY, companies.SMARTRECRUITERS, companies.WORKABLE) for slug, _, _ in lst}
CANDIDATES = [c for c in dict.fromkeys(CANDIDATES) if c not in HAVE]

ATS = {
    "greenhouse": lambda s: (f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs", lambda d: [j["title"] for j in d.get("jobs", [])]),
    "lever": lambda s: (f"https://api.lever.co/v0/postings/{s}?mode=json", lambda d: [j["text"] for j in d] if isinstance(d, list) else []),
    "ashby": lambda s: (f"https://api.ashbyhq.com/posting-api/job-board/{s}", lambda d: [j["title"] for j in d.get("jobs", [])]),
    "workable": lambda s: (f"https://apply.workable.com/api/v1/widget/accounts/{s}", lambda d: [j["title"] for j in d.get("jobs", [])]),
    "recruitee": lambda s: (f"https://{s}.recruitee.com/api/offers/", lambda d: [j["title"] for j in d.get("offers", [])]),
    "smartrecruiters": lambda s: (f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100", lambda d: [j["name"] for j in d.get("content", [])]),
}


def probe(args):
    ats, slug = args
    url, parse = ATS[ats](slug)
    try:
        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code != 200:
            return None
        titles = parse(r.json())
        if not titles:
            return None
        return {"ats": ats, "slug": slug, "jobs": len(titles), "data_jobs": sum(1 for t in titles if DATA.search(t))}
    except Exception:  # noqa: BLE001
        return None


tasks = [(a, s) for s in CANDIDATES for a in ATS]
with ThreadPoolExecutor(max_workers=24) as pool:
    hits = [h for h in pool.map(probe, tasks) if h]
hits.sort(key=lambda h: (h["slug"], h["ats"]))
json.dump({"hits": hits, "tried": CANDIDATES}, open("tools/probe.json", "w"), indent=1)
print(f"{len(hits)} boards found for {len(CANDIDATES)} candidates")
