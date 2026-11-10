"""Target companies by hiring platform (ATS). Every slug here was verified to respond.

Each entry: (board slug, display name, tags).
Tags: "vendor" = a data-tools company (its Solutions Architect / platform roles count as data roles),
      "supply" = supply chain / logistics company.
To find a new company's slug, add it to tools/probe.py and push; the probe writes tools/probe.json.
"""

GREENHOUSE = [
    # data tools
    ("databricks", "Databricks", ["vendor"]),
    ("fivetran", "Fivetran", ["vendor"]),
    ("starburst", "Starburst", ["vendor"]),
    ("singlestore", "SingleStore", ["vendor"]),
    ("cockroachlabs", "Cockroach Labs", ["vendor"]),
    ("collibra", "Collibra", ["vendor"]),
    ("dremio", "Dremio", ["vendor"]),
    ("imply", "Imply", ["vendor"]),
    ("neo4j", "Neo4j", ["vendor"]),
    ("nexla", "Nexla", ["vendor"]),
    ("pingcap", "PingCAP", ["vendor"]),
    ("sigmacomputing", "Sigma Computing", ["vendor"]),
    ("startree", "StarTree", ["vendor"]),
    ("yugabyte", "Yugabyte", ["vendor"]),
    ("mongodb", "MongoDB", ["vendor"]),
    ("elastic", "Elastic", ["vendor"]),
    ("celonis", "Celonis", ["vendor"]),
    ("grafanalabs", "Grafana Labs", []),
    # remote-first / global hirers
    ("thoughtworks", "Thoughtworks", []),
    ("gitlab", "GitLab", []),
    ("canonical", "Canonical", []),
    ("cloudflare", "Cloudflare", []),
    ("datadog", "Datadog", []),
    ("twilio", "Twilio", []),
    ("coinbase", "Coinbase", []),
    ("stripe", "Stripe", []),
    ("airtable", "Airtable", []),
    ("figma", "Figma", []),
    ("reddit", "Reddit", []),
    ("discord", "Discord", []),
    ("remotecom", "Remote.com", []),
    ("turing", "Turing", []),
    # supply chain / logistics
    ("flexport", "Flexport", ["supply"]),
    ("project44", "project44", ["supply"]),
    ("samsara", "Samsara", ["supply"]),
    ("gomotive", "Motive", ["supply"]),
    ("fourkites", "FourKites", ["supply"]),
    ("uberfreight", "Uber Freight", ["supply"]),
    ("shipmonk", "ShipMonk", ["supply"]),
    ("flexe", "Flexe", ["supply"]),
    ("narvar", "Narvar", ["supply"]),
    ("route", "Route", ["supply"]),
    ("pallet", "Pallet", ["supply"]),
    ("aftership", "AfterShip", ["supply"]),
]

LEVER = [
    ("acceldata", "Acceldata", ["vendor"]),
    ("ataccama", "Ataccama", ["vendor"]),
    ("hevodata", "Hevo Data", ["vendor"]),
    ("matillion", "Matillion", ["vendor"]),
    ("tinybird", "Tinybird", ["vendor"]),
    ("palantir", "Palantir", []),
    ("binance", "Binance", []),
    ("crypto", "Crypto.com", []),
    ("whoop", "WHOOP", []),
    ("toptal", "Toptal", []),
    ("kpler", "Kpler", ["supply"]),
    ("loadsmart", "Loadsmart", ["supply"]),
]

ASHBY = [
    ("snowflake", "Snowflake", ["vendor"]),
    ("clickhouse", "ClickHouse", ["vendor"]),
    ("airbyte", "Airbyte", ["vendor"]),
    ("astronomer", "Astronomer", ["vendor"]),
    ("hightouch", "Hightouch", ["vendor"]),
    ("motherduck", "MotherDuck", ["vendor"]),
    ("prefect", "Prefect", ["vendor"]),
    ("hex", "Hex", ["vendor"]),
    ("omni", "Omni Analytics", ["vendor"]),
    ("cube", "Cube", ["vendor"]),
    ("montecarlodata", "Monte Carlo", ["vendor"]),
    ("atlan", "Atlan", ["vendor"]),
    ("datafold", "Datafold", ["vendor"]),
    ("lightdash", "Lightdash", ["vendor"]),
    ("materialize", "Materialize", ["vendor"]),
    ("influxdata", "InfluxData", ["vendor"]),
    ("sisense", "Sisense", ["vendor"]),
    ("tigerdata", "Tiger Data", ["vendor"]),
    ("anyscale", "Anyscale", []),
    ("plaid", "Plaid", []),
    ("ramp", "Ramp", []),
    ("notion", "Notion", []),
    ("linear", "Linear", []),
    ("deel", "Deel", []),
    ("zapier", "Zapier", []),
    ("posthog", "PostHog", []),
    ("supabase", "Supabase", []),
    ("kraken.com", "Kraken", []),
    ("vercel", "Vercel", []),
    ("oyster", "Oyster HR", []),
    ("multiverse", "Multiverse", []),
    ("andela", "Andela", []),
]

SMARTRECRUITERS = [
    ("freshworks", "Freshworks", []),
    ("Visa", "Visa", []),
    ("Bosch", "Bosch", []),
    ("DHLGlobalForwarding", "DHL Global Forwarding", ["supply"]),
    ("Maersk", "Maersk", ["supply"]),
]

WORKABLE = [
    ("dlthub", "dltHub", ["vendor"]),
    ("hotjar", "Hotjar", []),
    ("doist", "Doist", []),
    ("toggl", "Toggl", []),
    ("smartcat", "Smartcat", []),
    ("intellias", "Intellias", []),
]
