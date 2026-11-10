"""Role and region classification for job postings."""
import re

ROLE_RULES = [
    ("Architecture", r"\b(data|solutions?|cloud|enterprise|analytics|platform|integration)\s+architect"),
    ("Engineering", r"\b(data|analytics|etl|elt|bi|dataops|big data|warehouse|lakehouse|integration|ml|machine learning)\s+(engineer|developer|engineering)"
                    r"|\bdata platform\b|\bdata infrastructure\b|\betl\b|\bsnowflake\b|\bdatabricks\b|\bdbt\b|\bspark\b|\binformatica\b|\bairflow\b"),
    ("Analytics", r"\b(data|business|product|marketing|bi|reporting|supply chain|operations|revenue|financial)\s+analy(st|tics)"
                  r"|\banalytics\s+(lead|manager|consultant|specialist)|\bbusiness intelligence\b|\btableau\b|\bpower ?bi\b|\blooker\b"),
    ("Science", r"\bdata scien(tist|ce)\b|\bdecision scien"),
]
ROLE_RES = [(name, re.compile(rx, re.I)) for name, rx in ROLE_RULES]

EXCLUDE_TITLE = re.compile(
    r"data ?cent(er|re)|technician|sales|account executive|recruit|intern\b|internship|"
    r"data entry|annotat|labell?er|clinical|nurse|payroll|legal|counsel|customer success|support specialist",
    re.I,
)


def role_of(title: str):
    if not title or EXCLUDE_TITLE.search(title):
        return None
    for name, rx in ROLE_RES:
        if rx.search(title):
            return name
    return None


SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|head|director|manager|architect)\b", re.I)


def level_of(title: str):
    return "Senior+" if SENIOR.search(title or "") else "Mid"


INDIA = re.compile(
    r"\bindia\b|bangalore|bengaluru|hyderabad|\bpune\b|chennai|mumbai|delhi|gurgaon|gurugram|noida|kolkata|ahmedabad|kochi|\bIST\b|asia/kolkata",
    re.I,
)
APAC = re.compile(r"\bapac\b|asia[- ]?pacific|\basia\b|\bsouth asia\b|\bsea\b|utc\s*\+\s*5", re.I)
WORLD = re.compile(
    r"worldwide|anywhere|\bglobal(ly)?\b|any (time ?zone|location|country)|work from anywhere|fully distributed|"
    r"\binternational\b|remote\s*\(?\s*(all|any)",
    re.I,
)
LOCKED = re.compile(
    r"\b(us|usa|u\.s\.a?\.?|united states|america|canada|uk|united kingdom|england|ireland|europe|european union|\beu\b|emea|"
    r"germany|france|spain|portugal|netherlands|poland|romania|nordics|latam|latin america|brazil|mexico|argentina|colombia|"
    r"australia|new zealand|japan|singapore|philippines|israel|south africa|nigeria|kenya|americas|north america|"
    r"cet|est|pst|cst|mst|et|pt)\b|\b(us|uk|eu)[- ]only|must (reside|be located|live) in",
    re.I,
)
REMOTE = re.compile(r"remote|distributed|work from home|wfh|anywhere|telecommut", re.I)

REGION_ORDER = {"India": 0, "APAC": 1, "Worldwide": 2, "Unclear": 3, "Locked": 4}


def region_of(location_text: str, is_remote: bool | None = None, restrictions: list | None = None):
    """Return India / APAC / Worldwide / Unclear / Locked, or None if not remote."""
    loc = (location_text or "").strip()
    remote = is_remote if is_remote is not None else bool(REMOTE.search(loc))
    if restrictions is not None:
        joined = " ".join(restrictions)
        if not restrictions:
            return "Worldwide" if remote or not loc else region_of(loc)
        if INDIA.search(joined):
            return "India"
        if APAC.search(joined):
            return "APAC"
        return "Locked"
    if INDIA.search(loc):
        # "Bangalore" onsite is still India-based; treat remote/hybrid alike for an India job seeker
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
