"""Role, stack and region classification for job postings."""
import re

# ---------- stack ----------
STACK = {
    "Snowflake": r"\bsnowflake\b",
    "Databricks": r"\bdatabricks\b",
    "dbt": r"\bdbt\b",
    "Spark": r"\b(py)?spark\b",
    "Airflow": r"\bairflow\b",
    "Kafka": r"\bkafka\b",
    "Flink": r"\bflink\b",
    "BigQuery": r"\bbig ?query\b",
    "Redshift": r"\bredshift\b",
    "Azure Data": r"\bazure data factory\b|\badf\b|\bsynapse\b|\bmicrosoft fabric\b|\bazure databricks\b",
    "AWS Glue": r"\baws glue\b|\bglue\b(?= (etl|jobs|catalog))|\bemr\b|\bathena\b",
    "Informatica": r"\binformatica\b|\bpowercenter\b|\biics\b",
    "Talend/SSIS": r"\btalend\b|\bssis\b|\bab ?initio\b|\bdatastage\b",
    "Fivetran": r"\bfivetran\b|\bairbyte\b|\bstitch\b",
    "Iceberg/Delta": r"\biceberg\b|\bdelta lake\b|\bhudi\b|\blakehouse\b",
    "Hadoop": r"\bhadoop\b|\bhive\b|\bhdfs\b",
    "Trino": r"\btrino\b|\bpresto\b|\bstarburst\b",
    "ClickHouse": r"\bclickhouse\b",
    "Power BI": r"\bpower ?bi\b",
    "Tableau": r"\btableau\b",
    "Looker": r"\blooker\b",
    "Python": r"\bpython\b",
    "SQL": r"\bsql\b",
    "Scala": r"\bscala\b",
}
STACK_RES = {k: re.compile(v, re.I) for k, v in STACK.items()}
CORE_STACK = set(STACK) - {"Python", "SQL"}  # generic languages don't prove a data role on their own


def stack_of(*texts):
    blob = " ".join(t for t in texts if t)
    return [k for k, rx in STACK_RES.items() if rx.search(blob)]


# ---------- role ----------
DATA_WORD = r"(data|analytics|etl|elt|bi|business intelligence|warehouse|lakehouse|big data|dataops|reporting)"

ROLE_RULES = [
    ("Architecture", rf"\b{DATA_WORD}\s+(solutions?\s+)?architect|\barchitect\b.*\b{DATA_WORD}\b|\b(integration|data platform)\s+architect"),
    ("Engineering", rf"\b{DATA_WORD}\s+(platform\s+|infrastructure\s+|pipeline\s+|integration\s+|software\s+)?(engineer|developer|engineering)"
                    rf"|\banalytics engineer|\b(etl|elt|bi|dwh|ssis|informatica|snowflake|databricks|spark|big data)\s+(engineer|developer|specialist|consultant|lead)"
                    rf"|\b(software|backend|platform|staff|senior|principal)\s+engineer\b.*\bdata\b|\bdata\b.*\b(software|backend)\s+engineer"),
    ("Analytics", r"\b(data|bi|business intelligence|reporting|insights|product data|supply chain data)\s+analy(st|tics)"
                  r"|\banalytics\s+(lead|manager|specialist|consultant|developer)|\bbi\s+(developer|analyst|lead|specialist)|\b(power ?bi|tableau|looker)\b"),
    ("Science", r"\bdata scien(tist|ce)\b|\bdecision scien"),
]
ROLE_RES = [(name, re.compile(rx, re.I)) for name, rx in ROLE_RULES]

# A generic title that is a data job only when the description is clearly data-heavy
GENERIC = re.compile(r"\bsolutions?\s+architect\b|\bintegration engineer\b|\bdata platform\b|\bdata infrastructure\b", re.I)

EXCLUDE_TITLE = re.compile(
    r"data ?cent(er|re)|technician|\bsales\b|account (executive|manager)|recruit|\bintern\b|internship|"
    r"data entry|annotat|label(l)?er|clinical|nurse|payroll|legal|counsel|customer success|support specialist|"
    r"product manager|program manager|project manager|\bmarketing\b|growth|\bgtm\b|go-to-market|revenue operations|"
    r"risk operations|monetization|market research|strategic partnerships|\bfinance\b|financial analyst|"
    r"\bai engineer\b|\bml engineer\b|machine learning engineer|\bllm\b|genai|generative ai|\bagent(ic)?\b|"
    r"kubernetes|security|devops|\bsre\b|frontend|front-end|mobile|ios|android",
    re.I,
)
DATA_IN_TITLE = re.compile(r"\bdata\b|analytics|\betl\b|warehouse|\bbi\b", re.I)


def role_of(title: str, stack=None, data_vendor=False):
    """Return a role bucket, or None if this is not a data role."""
    if not title:
        return None
    ex = EXCLUDE_TITLE.search(title)
    # allow e.g. "Machine Learning Data Engineer" or "Data Platform - Security Analytics" only if data is explicit
    if ex and not re.search(r"\bdata (engineer|architect|analyst)|analytics engineer", title, re.I):
        return None
    core = len(set(stack or []) & CORE_STACK)
    for name, rx in ROLE_RES:
        if rx.search(title):
            return name
    if GENERIC.search(title):
        if data_vendor or core >= 3:
            return "Architecture" if "architect" in title.lower() else "Engineering"
    return None


SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|head|director|manager|architect)\b", re.I)


def level_of(title: str):
    return "Senior+" if SENIOR.search(title or "") else "Mid"


# ---------- region ----------
INDIA = re.compile(
    r"\bindia\b|bangalore|bengaluru|hyderabad|\bpune\b|chennai|mumbai|delhi|gurgaon|gurugram|noida|kolkata|ahmedabad|kochi|\bIST\b|asia/kolkata",
    re.I,
)
APAC = re.compile(r"\bapac\b|asia[- ]?pacific|\basia\b|\bsouth asia\b|utc\s*\+\s*5", re.I)
WORLD = re.compile(
    r"worldwide|anywhere|\bglobal(ly)?\b|any (time ?zone|location|country)|work from anywhere|fully distributed|"
    r"\binternational\b|remote\s*\(?\s*(all|any)",
    re.I,
)
LOCKED = re.compile(
    r"\b(us|usa|u\.s\.a?\.?|united states|america|canada|uk|united kingdom|england|ireland|europe|european union|eu|emea|eea|"
    r"germany|france|spain|portugal|netherlands|poland|romania|greece|nordics|latam|latin america|brazil|mexico|argentina|colombia|"
    r"australia|new zealand|japan|singapore|philippines|israel|south africa|nigeria|kenya|americas|north america|uae|dubai|"
    r"cet|est|pst|cst|mst|et|pt)\b|\b(us|uk|eu)[- ]only|must (reside|be located|live) in",
    re.I,
)
REMOTE = re.compile(r"remote|distributed|work from home|wfh|anywhere|telecommut", re.I)

REGION_ORDER = {"India": 0, "APAC": 1, "Worldwide": 2, "Unclear": 3, "Locked": 4}


def region_of(location_text: str, is_remote: bool | None = None, restrictions: list | None = None):
    """Return India / APAC / Worldwide / Unclear / Locked, or None if not remote and not in India."""
    loc = (location_text or "").strip()
    remote = is_remote if is_remote is not None else bool(REMOTE.search(loc))
    if restrictions is not None:
        if not restrictions:
            return "Worldwide"
        joined = " ".join(restrictions)
        if INDIA.search(joined):
            return "India"
        if APAC.search(joined):
            return "APAC"
        return "Locked"
    if INDIA.search(loc):
        return "India"
    if not remote:
        return None
    if APAC.search(loc):
        return "APAC"
    if WORLD.search(loc):
        return "Worldwide"
    if LOCKED.search(loc):
        return "Locked"
    return "Unclear"


SUPPLY = re.compile(
    r"supply chain|logistic|freight|\btms\b|transportation management|warehouse management|\bwms\b|shipping|carrier|"
    r"fulfil?ment|procure|inventory|blue yonder|manhattan associates|\bedi\b",
    re.I,
)


def is_supply(*texts):
    return any(SUPPLY.search(t or "") for t in texts)
