"""Shared helpers for the Medal of Honor citation pipeline.

The roster is compiled from public-domain U.S. government texts.
Nothing in this module copies prose from the Congressional Medal of
Honor Society, the National Medal of Honor Museum, Home of Heroes,
Military Times, or Honoring American Troops.
"""

from __future__ import annotations

import html
import re
import unicodedata
from datetime import datetime

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

# Historical abbreviations used in the Army citation index.
STATE_ABBR = {
    "ala": "Alabama",
    "alabama": "Alabama",
    "alaska": "Alaska",
    "ariz": "Arizona",
    "arizona": "Arizona",
    "ark": "Arkansas",
    "arkansas": "Arkansas",
    "calif": "California",
    "california": "California",
    "cal": "California",
    "colo": "Colorado",
    "colorado": "Colorado",
    "col": "Colorado",
    "conn": "Connecticut",
    "connecticut": "Connecticut",
    "ct": "Connecticut",
    "del": "Delaware",
    "delaware": "Delaware",
    "d.c.": "District of Columbia",
    "d. c.": "District of Columbia",
    "dc": "District of Columbia",
    "district of columbia": "District of Columbia",
    "washington dc": "District of Columbia",
    "washington d.c.": "District of Columbia",
    "fla": "Florida",
    "florida": "Florida",
    "ga": "Georgia",
    "georgia": "Georgia",
    "hawaii": "Hawaii",
    "idaho": "Idaho",
    "ill": "Illinois",
    "illinois": "Illinois",
    "ind": "Indiana",
    "indiana": "Indiana",
    "iowa": "Iowa",
    "kans": "Kansas",
    "kan": "Kansas",
    "kas": "Kansas",
    "kansas": "Kansas",
    "ky": "Kentucky",
    "kentucky": "Kentucky",
    "la": "Louisiana",
    "louisiana": "Louisiana",
    "maine": "Maine",
    "me": "Maine",
    "md": "Maryland",
    "maryland": "Maryland",
    "mass": "Massachusetts",
    "massachusetts": "Massachusetts",
    "mich": "Michigan",
    "michigan": "Michigan",
    "minn": "Minnesota",
    "minnesota": "Minnesota",
    "miss": "Mississippi",
    "mississippi": "Mississippi",
    "mo": "Missouri",
    "missouri": "Missouri",
    "mont": "Montana",
    "montana": "Montana",
    "nebr": "Nebraska",
    "neb": "Nebraska",
    "nebraska": "Nebraska",
    "nev": "Nevada",
    "nevada": "Nevada",
    "n.h.": "New Hampshire",
    "n. h.": "New Hampshire",
    "nh": "New Hampshire",
    "new hampshire": "New Hampshire",
    "n.j.": "New Jersey",
    "n. j.": "New Jersey",
    "nj": "New Jersey",
    "new jersey": "New Jersey",
    "n.mex.": "New Mexico",
    "n. mex.": "New Mexico",
    "n.mex": "New Mexico",
    "n mex": "New Mexico",
    "new mexico": "New Mexico",
    "n.y.": "New York",
    "n. y.": "New York",
    "ny": "New York",
    "new york": "New York",
    "n.c.": "North Carolina",
    "n. c.": "North Carolina",
    "nc": "North Carolina",
    "north carolina": "North Carolina",
    "n.dak.": "North Dakota",
    "n. dak.": "North Dakota",
    "n dak": "North Dakota",
    "north dakota": "North Dakota",
    "ohio": "Ohio",
    "okla": "Oklahoma",
    "oklahoma": "Oklahoma",
    "ore": "Oregon",
    "oreg": "Oregon",
    "oregon": "Oregon",
    "pa": "Pennsylvania",
    "penn": "Pennsylvania",
    "pennsylvania": "Pennsylvania",
    "r.i.": "Rhode Island",
    "r. i.": "Rhode Island",
    "ri": "Rhode Island",
    "rhode island": "Rhode Island",
    "s.c.": "South Carolina",
    "s. c.": "South Carolina",
    "sc": "South Carolina",
    "south carolina": "South Carolina",
    "s.dak.": "South Dakota",
    "s. dak.": "South Dakota",
    "s dak": "South Dakota",
    "south dakota": "South Dakota",
    "tenn": "Tennessee",
    "tennessee": "Tennessee",
    "tex": "Texas",
    "texas": "Texas",
    "utah": "Utah",
    "vt": "Vermont",
    "vermont": "Vermont",
    "va": "Virginia",
    "virginia": "Virginia",
    "wash": "Washington",
    "washington": "Washington",
    "w.va.": "West Virginia",
    "w. va.": "West Virginia",
    "w.va": "West Virginia",
    "w va": "West Virginia",
    "west virginia": "West Virginia",
    "wis": "Wisconsin",
    "wisc": "Wisconsin",
    "wisconsin": "Wisconsin",
    "wyo": "Wyoming",
    "wyoming": "Wyoming",
}

SUFFIXES = {
    "jr": "Jr.",
    "jr.": "Jr.",
    "sr": "Sr.",
    "sr.": "Sr.",
    "ii": "II",
    "iii": "III",
    "iv": "IV",
    "2d": "2d",
    "2nd": "2d",
    "3d": "3d",
    "3rd": "3d",
}

LABEL_RE = re.compile(
    r"\b(Rank and organization|Place and date|Entered service at|Enlisted in|"
    r"Birth|Born|Date of issue|Accredited to|G\.O\. No\.|Citation)\s*[:.]?",
    re.IGNORECASE,
)

DATE_TOKEN = (
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.?"
)

# Order matters: longer, more specific patterns first.
DATE_PATTERNS = [
    # 15 and 16 March 1945
    re.compile(rf"(\d{{1,2}})\s+and\s+(\d{{1,2}})\s+({DATE_TOKEN})\s+(\d{{4}})", re.I),
    # from 19 to 22 February 1945
    re.compile(rf"from\s+(\d{{1,2}})\s+to\s+(\d{{1,2}})\s+({DATE_TOKEN})\s+(\d{{4}})", re.I),
    # 9 June 1871 – 10 June 1871
    re.compile(
        rf"(\d{{1,2}})\s+({DATE_TOKEN})\s+(\d{{4}})\s*[–\-to]+\s*(\d{{1,2}})\s+({DATE_TOKEN})\s+(\d{{4}})",
        re.I,
    ),
    # June 9, 1871 – June 10, 1871
    re.compile(
        rf"({DATE_TOKEN})\s+(\d{{1,2}}),?\s+(\d{{4}})\s*[–\-to]+\s*({DATE_TOKEN})\s+(\d{{1,2}}),?\s+(\d{{4}})",
        re.I,
    ),
    # June 14-15, 1953 or June 14–15, 1953
    re.compile(rf"({DATE_TOKEN})\s+(\d{{1,2}})\s*[–\-]\s*(\d{{1,2}}),?\s+(\d{{4}})", re.I),
    # 14-15 June 1953
    re.compile(rf"(\d{{1,2}})\s*[–\-]\s*(\d{{1,2}})\s+({DATE_TOKEN})\s+(\d{{4}})", re.I),
    # 12 November 1864
    re.compile(rf"(\d{{1,2}})\s+({DATE_TOKEN})\s+(\d{{4}})", re.I),
    # November 12, 1864
    re.compile(rf"({DATE_TOKEN})\s+(\d{{1,2}}),?\s+(\d{{4}})", re.I),
    # November 1864
    re.compile(rf"({DATE_TOKEN})\s+(\d{{4}})", re.I),
]

DEATH_PHRASES = [
    "posthumously",
    "at the cost of his own life",
    "at the cost of her own life",
    "at the cost of his life",
    "at the cost of her life",
    "gave his life",
    "gave her life",
    "sacrificed his life",
    "sacrificed her life",
    "lost his life",
    "lost her life",
    "he was killed",
    "she was killed",
    "was mortally wounded",
    "fell mortally wounded",
    "mortally wounded",
    "fell dead",
    "until he was killed",
    "until she was killed",
    "killed in action",
]


def squash(text: str) -> str:
    text = html.unescape(text or "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def blankish(value: str | None) -> bool:
    if not value:
        return True
    v = value.strip(" .;-")
    return v == "" or set(v) <= set("-—–")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "record"


def _cap_token(token: str) -> str:
    token = token.strip()
    if not token:
        return ""
    if re.fullmatch(r"[A-Za-z]\.?", token):
        return token[0].upper() + "."
    token = token.strip(".")
    if token.lower().rstrip(".") in SUFFIXES:
        return SUFFIXES[token.lower().rstrip(".")]
    if re.fullmatch(r"[IVX]{2,4}", token):
        return token.upper()
    if "'" in token or "’" in token:
        parts = re.split(r"['’]", token)
        return "'".join(p.capitalize() for p in parts if p != "" or True).replace("''", "'")
    if token.startswith("Mac") and len(token) > 3 and token[3].isupper():
        return "Mac" + token[3:].capitalize()
    if token.startswith("Mc") and len(token) > 2 and token[2].isupper():
        return "Mc" + token[2:].capitalize()
    if token.isupper() and token.lower().startswith("mc") and len(token) > 2:
        return "Mc" + token[2:].capitalize()
    return token.capitalize()


def format_indexed_name(raw: str) -> dict:
    """Turn 'MacARTHUR, ARTHUR, JR.' into display and sort fields."""
    cleaned = squash(raw).lstrip("*").strip()
    cleaned = cleaned.replace(" ,", ",")
    if "," not in cleaned:
        display = " ".join(_cap_token(p) for p in cleaned.split())
        return {
            "display": display,
            "sort": display,
            "last": display,
            "first": "",
            "middle": "",
            "suffix": "",
        }
    last_raw, rest = cleaned.split(",", 1)
    rest_parts = [p.strip() for p in rest.split(",") if p.strip()]
    given_tokens: list[str] = []
    suffix = ""
    for part in rest_parts:
        bits = part.split()
        kept = []
        for bit in bits:
            key = bit.lower().rstrip(".")
            if key in SUFFIXES or re.fullmatch(r"[IVX]{2,4}", bit):
                suffix = SUFFIXES.get(key, bit.upper())
            else:
                kept.append(bit)
        given_tokens.extend(kept)
    last = " ".join(_cap_token(p) for p in last_raw.split())
    given = [_cap_token(p) for p in given_tokens]
    first = given[0] if given else ""
    middle = " ".join(given[1:]) if len(given) > 1 else ""
    display_bits = [first, middle, last]
    display = " ".join(b for b in display_bits if b)
    if suffix:
        display = f"{display} {suffix}".strip()
    sort = ", ".join(p for p in [last, " ".join(b for b in [first, middle] if b)] if p)
    if suffix:
        sort = f"{sort} {suffix}"
    return {
        "display": display,
        "sort": sort,
        "last": last,
        "first": first,
        "middle": middle,
        "suffix": suffix,
    }


def name_identity(parts: dict) -> str:
    middle_initial = ""
    if parts.get("middle"):
        middle_initial = parts["middle"][0].lower()
    return "|".join(
        [
            slugify(parts.get("last", "")),
            slugify(parts.get("first", "")),
            middle_initial,
            slugify(parts.get("suffix", "")),
        ]
    )


def parse_labeled_block(text: str) -> dict:
    text = squash(text)
    matches = list(LABEL_RE.finditer(text))
    fields: dict[str, str] = {}
    if not matches:
        return {"citation": text, "fields": fields}
    # Citation consumes the remainder so later colons stay inside it.
    citation_at = next((m.start() for m in matches if m.group(1).lower() == "citation"), None)
    usable = [m for m in matches if citation_at is None or m.start() <= citation_at]
    for i, match in enumerate(usable):
        key = match.group(1).lower()
        start = match.end()
        end = usable[i + 1].start() if i + 1 < len(usable) else len(text)
        if key == "citation":
            end = len(text)
        value = squash(text[start:end]).strip(" ;")
        fields[key] = value
    citation = fields.get("citation", "")
    # Drop the "for more information" trailer the Army feature blurbs append.
    citation = re.split(r"\bFor more information\b", citation, maxsplit=1, flags=re.I)[0].strip()
    return {"citation": citation, "fields": fields}


def _month_num(token: str) -> int:
    return MONTHS[token.lower().rstrip(".")]


def _iso(year: int, month: int, day: int | None = None) -> str | None:
    try:
        if day is None:
            return f"{year:04d}-{month:02d}"
        datetime(year, month, day)
        return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        return None


def parse_date_span(raw: str | None) -> dict:
    """Return start/end ISO dates and a year when a date can be read."""
    result = {"start": None, "end": None, "year": None, "label": None}
    if not raw or blankish(raw):
        return result
    text = squash(raw)
    result["label"] = text
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        try:
            if pattern is DATE_PATTERNS[0] or pattern is DATE_PATTERNS[1]:
                d1, d2, month, year = groups
                result["start"] = _iso(int(year), _month_num(month), int(d1))
                result["end"] = _iso(int(year), _month_num(month), int(d2))
            elif pattern is DATE_PATTERNS[2]:
                d1, m1, y1, d2, m2, y2 = groups
                result["start"] = _iso(int(y1), _month_num(m1), int(d1))
                result["end"] = _iso(int(y2), _month_num(m2), int(d2))
            elif pattern is DATE_PATTERNS[3]:
                m1, d1, y1, m2, d2, y2 = groups
                result["start"] = _iso(int(y1), _month_num(m1), int(d1))
                result["end"] = _iso(int(y2), _month_num(m2), int(d2))
            elif pattern is DATE_PATTERNS[4]:
                month, d1, d2, year = groups
                result["start"] = _iso(int(year), _month_num(month), int(d1))
                result["end"] = _iso(int(year), _month_num(month), int(d2))
            elif pattern is DATE_PATTERNS[5]:
                d1, d2, month, year = groups
                result["start"] = _iso(int(year), _month_num(month), int(d1))
                result["end"] = _iso(int(year), _month_num(month), int(d2))
            elif pattern is DATE_PATTERNS[6]:
                day, month, year = groups
                result["start"] = _iso(int(year), _month_num(month), int(day))
                result["end"] = result["start"]
            elif pattern is DATE_PATTERNS[7]:
                month, day, year = groups
                result["start"] = _iso(int(year), _month_num(month), int(day))
                result["end"] = result["start"]
            else:
                month, year = groups
                result["start"] = _iso(int(year), _month_num(month), None)
                result["end"] = result["start"]
        except (ValueError, KeyError):
            continue
        if result["start"]:
            result["year"] = int(result["start"][:4])
            result["label"] = match.group(0).replace(" - ", "–").replace(" -", "–")
            return result
    year_only = re.search(r"\b(18|19|20)\d{2}\b", text)
    if year_only:
        result["year"] = int(year_only.group(0))
    return result


def split_place_and_date(raw: str | None) -> tuple[str | None, dict]:
    if not raw or blankish(raw):
        return None, parse_date_span(None)
    text = squash(raw)
    dates = parse_date_span(text)
    place = text
    if dates["label"] and dates["label"] in text:
        place = text.replace(dates["label"], " ")
    place = re.sub(r"\s*[–\-]\s*", " ", place)
    place = squash(place).strip(" ,;.-")
    place = re.sub(r"^(?:at|near|in|aboard|on board)\s+", "", place, flags=re.I)
    if blankish(place):
        place = None
    return place, dates


def find_state(raw: str | None) -> str | None:
    if not raw or blankish(raw):
        return None
    text = squash(raw).lower().replace(".", ".")
    # Prefer the last comma-separated piece, where the state usually sits.
    pieces = [p.strip(" .;") for p in text.split(",")]
    candidates = pieces[-2:] + [text]
    # Also try "washington, d.c." as a pair.
    if "d.c" in text or "district of columbia" in text:
        return "District of Columbia"
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate in STATE_ABBR:
            return STATE_ABBR[candidate]
        # "n.y" without the trailing dot already handled; try stripping dots.
        dotted = candidate.replace(" ", "")
        if dotted in STATE_ABBR:
            return STATE_ABBR[dotted]
    # Scan tokens from the end.
    tokens = re.findall(r"[a-z.]+", text)
    for size in (3, 2, 1):
        if len(tokens) < size:
            continue
        phrase = " ".join(tokens[-size:])
        if phrase in STATE_ABBR:
            return STATE_ABBR[phrase]
    return None


def _branch_in(text: str) -> str | None:
    low = text.lower()
    if "coast guard" in low:
        return "U.S. Coast Guard"
    if "marine corps" in low or "usmc" in low:
        return "U.S. Marine Corps"
    if re.search(r"\b(navy|naval|u\.s\.n\.)\b", low) or "petty officer" in low:
        return "U.S. Navy"
    if re.search(r"\bair force\b", low) and "army air" not in low:
        return "U.S. Air Force"
    if "army air" in low or "air corps" in low or "air service" in low:
        return "U.S. Army Air Forces"
    if "army" in low:
        return "U.S. Army"
    if re.search(r"\bu\.?s\.?s\.?\s+[a-z]", low):
        return "U.S. Navy"
    return None


def detect_branch(rank_org: str | None, citation: str | None = None) -> str:
    """Prefer the service named in the rank-and-organization line."""
    if rank_org:
        found = _branch_in(rank_org)
        if found:
            return found
    if citation:
        # Do not treat a passing mention of naval gunfire as a Navy award.
        head = re.sub(r"\bnaval gunfire\b", " ", citation[:500], flags=re.I)
        found = _branch_in(head)
        if found:
            return found
    return "U.S. Army"


def citation_implies_death(citation: str | None) -> bool:
    if not citation:
        return False
    low = citation.lower()
    return any(phrase in low for phrase in DEATH_PHRASES)


def tidy_place(place: str | None) -> str | None:
    """Drop leftover date fragments from a place string."""
    if not place:
        return None
    text = re.split(r"\b(?:entered service at|accredited to)\b", place, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"\b(?:from|between)\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,2}\b", " ", text)
    text = re.sub(r"\b(?:and|to)\b", " ", text, flags=re.I)
    text = text.replace(".", " ")
    text = re.sub(
        r",?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\b.*$",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+,", ",", text)
    text = squash(text).strip(" ,;-")
    text = re.sub(r"^(?:at|near|in|aboard|on board|on)\s+", "", text, flags=re.I)
    if blankish(text) or len(text) < 3:
        return None
    return clean_place_display(text)


def clean_place_display(place: str | None) -> str | None:
    if not place:
        return None
    text = squash(place)
    # Expand a trailing state abbreviation for display.
    match = re.search(r",\s*([A-Za-z.\s]+)$", text)
    if match:
        state = find_state(match.group(1))
        if state:
            text = text[: match.start()] + ", " + state
    # Title-case only all-caps locality words, leaving short abbreviations alone.
    def fix(word: str) -> str:
        if word.isupper() and len(word) > 2:
            return word.capitalize()
        return word

    return " ".join(fix(w) for w in text.split())


def ship_from_text(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"\bU\.?\s*S\.?\s*S\.?\s+([A-Z][A-Za-z0-9'’-]+)", text)
    if match:
        return f"USS {match.group(1)}"
    return None
