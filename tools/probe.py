"""Find which hiring platform each candidate company uses. Writes tools/probe.json."""
import json
import re
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "shoreless.dev/1.0 (board probe)"}
DATA = re.compile(r"data|analytics|etl|bi engineer|business intelligence|warehouse", re.I)

CANDIDATES = """
fourkites shipbob shippo stord o9solutions o9 transfix shipwell plaid dbtlabs dbt-labs clickhouse alation
informatica matillion thoughtspot sisense hashicorp postman toptal andela easypost deliverr altana everstream
anvyl parade logixboard terminal49 emerge arc dagster dagsterlabs dlthub dlt-hub tinybird sourcegraph augment
augmentcode flockfreight flock-freight pallet snowflake snowflakecomputing confluent thoughtworks atlan hasura
browserstack freshworks razorpay sigmacomputing sigma census rudderstack estuary materialize firebolt imply
startree onehouse dremio ataccama secoda metaplane datafold greatexpectations great-expectations elementary
hevodata hevo nexla celonis kpler flexe kinaxis coupa gorgias velocityglobal multiverse sardine chainalysis
anyscale weaviate pinecone qdrant labelbox scale scaleai hightouch census tecton fivetran starburst
singlestore cockroachlabs grafanalabs neo4j redpanda redpandadata timescale tigerdata influxdata couchbase
yugabyte pingcap aiven instaclustr cloudera teradata talend qlik domo looker mode omni lightdash preset
astronomer prefect airbyte motherduck montecarlodata bigeye acceldata soda sodadata collibra
flexport project44 samsara gomotive motive convoy uberfreight loadsmart project-44 shipmonk shiphero
deliverydotcom route parcelperform shipup narvar aftership locus locusdotsh fareye shiprocket delhivery
blueyonder e2open manhattanassociates descartes gocomet freightify flock
""".split()
CANDIDATES = list(dict.fromkeys(CANDIDATES))

ATS = {
    "greenhouse": lambda s: (f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs", lambda d: [j["title"] for j in d.get("jobs", [])]),
    "lever": lambda s: (f"https://api.lever.co/v0/postings/{s}?mode=json", lambda d: [j["text"] for j in d] if isinstance(d, list) else []),
    "ashby": lambda s: (f"https://api.ashbyhq.com/posting-api/job-board/{s}", lambda d: [j["title"] for j in d.get("jobs", [])]),
    "workable": lambda s: (f"https://apply.workable.com/api/v1/widget/accounts/{s}", lambda d: [j["title"] for j in d.get("jobs", [])]),
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
