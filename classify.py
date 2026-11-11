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
HARD_EXCLUDE = re.compile(r"\bintern(ship)?\b|\btrainee\b|\btrainer\b|\btutor\b|\bfreelance trainer\b|\bteacher\b", re.I)
DATA_IN_TITLE = re.compile(r"\bdata\b|analytics|\betl\b|warehouse|\bbi\b", re.I)


def role_of(title: str, stack=None, data_vendor=False):
    """Return a role bucket, or None if this is not a data role."""
    if not title:
        return None
    if HARD_EXCLUDE.search(title):
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

_GENERIC_LOC = re.compile(r"remote|distributed|work from home|wfh|home[- ]?based|telecommut\w*|hybrid|fully|100%|flexible|n/?a|[\W_]+", re.I)

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
    # A named place that is not India, APAC or worldwide means the role is tied to that place.
    if LOCKED.search(loc) or _GENERIC_LOC.sub(" ", loc).strip():
        return "Locked"
    return "Unclear"


SUPPLY = re.compile(
    r"supply chain|logistic|freight|\btms\b|transportation management|warehouse management|\bwms\b|shipping|carrier|"
    r"fulfil?ment|procure|inventory|blue yonder|manhattan associates|\bedi\b",
    re.I,
)


SUPPLY_STRONG = re.compile(
    r"supply chain|logistics|freight|\btms\b|transportation management|warehouse management|\bwms\b|blue yonder|manhattan (associates|wms|active)",
    re.I,
)


def is_supply(title, company, desc=""):
    """True for supply-chain roles: named in the title or company, or mentioned repeatedly in the description."""
    if SUPPLY.search(title or "") or SUPPLY_STRONG.search(company or ""):
        return True
    return len(SUPPLY_STRONG.findall(desc or "")) >= 3


# ---------- pay ----------
SYM = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "INR": "\u20b9", "CAD": "C$", "AUD": "A$", "SGD": "S$"}


def _n(x, cur):
    if cur == "INR" and x >= 1e5:
        return f"{x / 1e5:.3g}L"
    if x >= 1000:
        return f"{x / 1000:.3g}k"
    return f"{x:g}"


def fmt_pay(pay):
    """{'min','max','cur','per'} or {'text'} -> short display string."""
    if not pay:
        return ""
    if pay.get("text"):
        return pay["text"]
    lo, hi, cur, per = pay["min"], pay["max"], pay.get("cur") or "USD", pay.get("per") or "yr"
    if per == "yr" and hi < 500:
        per = "hr"
    sym = SYM.get(cur, cur + " ")
    body = f"{sym}{_n(lo, cur)}" if _n(lo, cur) == _n(hi, cur) else f"{sym}{_n(lo, cur)}\u2013{_n(hi, cur)}"
    return f"{body}/{per}"


_CUR = r"(US\$|\$|USD|\u20ac|EUR|\u00a3|GBP|\u20b9|INR|Rs\.?)"
_AMT = r"(\d{1,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])"
_RANGE = re.compile(_CUR + r"\s?" + _AMT + r"\s?(?:-|\u2013|\u2014|to)\s?" + _CUR + r"?\s?" + _AMT)
_LPA = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?(?:-|\u2013|to)\s?(\d{1,3}(?:\.\d+)?)\s?(?:LPA|lakhs?\b|lacs?\b)", re.I)
_CURMAP = {"$": "USD", "US$": "USD", "USD": "USD", "\u20ac": "EUR", "EUR": "EUR", "\u00a3": "GBP", "GBP": "GBP",
           "\u20b9": "INR", "INR": "INR", "RS": "INR", "RS.": "INR"}


def _amt(t):
    t = t.replace(",", "").strip().lower()
    return float(t[:-1]) * 1000 if t.endswith("k") else float(t)


def pay_from_text(text):
    """Find a stated pay range in a job description. Conservative: needs a currency and a range."""
    if not text:
        return ""
    m = _LPA.search(text)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if 1 <= lo <= hi <= 200:
            return fmt_pay({"min": lo * 1e5, "max": hi * 1e5, "cur": "INR", "per": "yr"})
    m = _RANGE.search(text)
    if m:
        lo, hi = _amt(m.group(2)), _amt(m.group(4))
        if 1000 <= lo <= hi <= lo * 4:
            tail = text[m.end():m.end() + 40].lower()
            per = "hr" if "hour" in tail else "mo" if "month" in tail else "yr"
            return fmt_pay({"min": lo, "max": hi, "cur": _CURMAP.get(m.group(1).upper(), "USD"), "per": per})
    return ""


# ---------- region hints in the description ----------
_INDIA_DESC = re.compile(
    r"(remote|anywhere)\s*[\(\-\u2013,]?\s*(in|from|within)?\s*india\b|\bindia\s*\(?\s*remote|"
    r"(based|located|reside|residing|candidates?|applicants?) (in|from) india\b|work(ing)? from india\b|\bindia[- ]based\b|"
    r"open to (candidates|applicants|talent)[^.]{0,60}\bindia\b|(hire|hiring|employ)[^.]{0,20} in[^.]{0,80}\bindia\b|"
    r"\b(ist|indian standard time)\b[^.]{0,30}(hours|time ?zone|overlap)",
    re.I,
)
_WORLD_DESC = re.compile(
    r"work from anywhere|anywhere in the world|from anywhere\b|worldwide|globally distributed|fully distributed|"
    r"any (country|time ?zone|location)|hire (globally|internationally|anywhere)|location[- ]agnostic|remote[- ]first[^.]{0,40}(global|world)",
    re.I,
)
_LOCK_DESC = re.compile(
    r"(authori[sz]ed|eligible|right|legally (able|permitted)) to work in (the )?(u\.?s\.?a?\b|united states|uk\b|united kingdom|canada|eu\b|europe|germany|australia)|"
    r"must (be|reside|live|be located|be based)[^.]{0,30}(in|within) (the )?(u\.?s\.?a?\b|united states|uk\b|united kingdom|canada|eu\b|europe|emea|americas|latam|australia)|"
    r"\b(us|u\.s\.|uk|eu|canada)[- ](only|based (candidates|applicants))|(us|u\.s\.) citizens?|security clearance|"
    r"(based|located|residing) in (the )?(united states|u\.s\.|usa|uk|united kingdom|canada|europe|european union|emea|latam|latin america)",
    re.I,
)


def region_from_desc(desc):
    """For remote roles whose location field says nothing useful: look for a clear statement in the description."""
    d = (desc or "")[:8000]
    if _INDIA_DESC.search(d):
        return "India"
    if _LOCK_DESC.search(d):
        return "Locked"
    if _WORLD_DESC.search(d):
        return "Worldwide"
    return None


_FX = {"USD": 1, "EUR": 1.08, "GBP": 1.27, "INR": 0.012, "CAD": 0.73, "AUD": 0.66, "SGD": 0.75}
_PER = {"yr": 1, "mo": 12, "hr": 2000}


def pay_usd(pay, text=""):
    """Rough annual USD figure (top of range) used only for sorting. 0 when unknown."""
    if pay and not pay.get("text"):
        per = pay.get("per") or "yr"
        if per == "yr" and pay["max"] < 500:
            per = "hr"
        return int(pay["max"] * _FX.get(pay.get("cur") or "USD", 1) * _PER[per])
    t = (pay or {}).get("text") or text or ""
    lakh = re.search(r"\u20b9\s?[\d.]+L?\u2013?([\d.]+)L", t) or re.search(r"\u20b9\s?([\d.]+)L", t)
    if lakh:
        return int(float(lakh.group(1)) * 1e5 * _FX["INR"])
    nums = re.findall(r"(\d+(?:[.,]\d+)?)\s?([kK])?", t.replace(",", ""))
    vals = [float(n) * (1000 if k else 1) for n, k in nums if n]
    if not vals:
        return 0
    v = max(vals)
    cur = "EUR" if "\u20ac" in t else "GBP" if "\u00a3" in t else "INR" if "\u20b9" in t else "USD"
    per = "hr" if "/hr" in t else "mo" if "/mo" in t else "yr"
    return int(v * _FX[cur] * _PER[per])
