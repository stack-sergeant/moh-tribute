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
    # The Army index prints at least one "JR." suffix as "IR."
    "ir": "Jr.",
    "ir.": "Jr.",
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

# Citation is handled separately. A colon, a bare "Citation" before the
# prose, and the word dropped into the middle of a citation are different.
LABEL_RE = re.compile(
    r"\b(?:"
    r"(Rank and organization|Places and dates|Place and date|Place and dare|Action date|"
    r"Entered service at|Enlisted in|Birth|Born|Date of issue|Accredited to|Appointed from|"
    r"G\.O\. No\.)\s*[:.]?"
    r"|(Rank|Organization|Place|Date)\s*:"
    r")",
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

# Phrases that attribute death to the recipient. Bare "mortally wounded" and
# "killed in action" are not included: citations use them for comrades and enemies.
RECIPIENT_DEATH_PHRASES = [
    "posthumously",
    "at the cost of his own life",
    "at the cost of her own life",
    "at the cost of his life",
    "at the cost of her life",
    "gave his life",
    "gave her life",
    "sacrificed his life",
    "sacrificed her life",
    "sacrificing his own life",
    "sacrificing her own life",
    "he was killed",
    "she was killed",
    "until he was killed",
    "until she was killed",
    "he was mortally wounded",
    "she was mortally wounded",
    "although mortally wounded",
    "cost him his life",
    "cost her her life",
    "laying down his own life",
    "laying down her own life",
]


# Indexed-name tokens the Army snapshot misspelled with l/I.
# McGuire and McGarity are spelled that way in their own citation text.
# McIntosh is the l/I error in "Mclntosh"; the citation repeats the bad OCR,
# and the audit names this correction.
OCR_NAME_TOKENS = {
    "mcgulre": "McGuire",
    "mcgarlty": "McGarity",
    "mclntosh": "McIntosh",
}


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
    if "-" in token.strip("-"):
        return "-".join(_cap_token(part) for part in token.split("-"))
    mapped = OCR_NAME_TOKENS.get(token.lower().strip("."))
    if mapped:
        return mapped
    # The index prints the middle initial I as the digit 1 (Richard 1. Bong).
    if re.fullmatch(r"1\.?", token):
        return "I."
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


def _surname_first_without_comma(cleaned: str) -> str | None:
    tokens = cleaned.split()
    if len(tokens) < 3 or not tokens[0].isupper() or len(tokens[0]) < 4:
        return None
    if not re.fullmatch(r"[A-Za-z]\.?", tokens[-1]):
        return None
    if not all(token.isupper() or re.fullmatch(r"[A-Za-z]\.?", token) for token in tokens):
        return None
    return tokens[0] + ", " + " ".join(tokens[1:])


def format_indexed_name(raw: str) -> dict:
    """Turn 'MacARTHUR, ARTHUR, JR.' into display and sort fields."""
    cleaned = squash(raw).lstrip("*").strip()
    cleaned = cleaned.replace(" ,", ",")
    # "PITSENBARGER WILLIAM H." has no comma. The last token is an initial
    # and the first token is the surname.
    if "," not in cleaned:
        flipped = _surname_first_without_comma(cleaned)
        if flipped:
            cleaned = flipped
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
    display = re.sub(r" {2,}", " ", display).strip()
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


def _strip_citation_trailer(citation: str) -> str:
    return re.split(r"\bFor more info(?:rmation)?\b", citation or "", maxsplit=1, flags=re.I)[0].strip()


def _label_key(match: re.Match) -> str:
    raw = next(group for group in match.groups() if group)
    key = raw.lower()
    if key in {"place and dare", "places and dates"}:
        return "place and date"
    return key


_CITATION_LABEL_RE = re.compile(
    r"\b(?:Citation|Citatation|Citatian|Citarion|Citatlon|Cltation|Cltatlon|Cita\s+tion)\b\s*[:.]?",
    re.I,
)


_FIELD_LEAD = re.compile(
    r"^(?:Rank and organization|Place and date|Entered service at|Entered service|"
    r"Date and place of birth|Date of issue|Accredited to|Appointed from|Born|Birth|"
    r"G\.O\. No\.)\s*:\s*",
    re.I,
)


def _narrative_offset(text: str) -> int | None:
    """Index where the prose starts after a run of 'Label: value.' fields."""
    if not _FIELD_LEAD.match(text):
        return None
    pos = 0
    guard = 0
    while guard < 12:
        guard += 1
        lead = _FIELD_LEAD.match(text[pos:])
        if not lead:
            return pos or None
        rest = text[pos + lead.end() :]
        cut = None
        for mark in re.finditer(r"\.\s+", rest):
            before = rest[mark.start() - 1] if mark.start() else ""
            earlier = rest[mark.start() - 2] if mark.start() >= 2 else ""
            # "U.S. Army" is an abbreviation, not the end of the field.
            if before.isupper() and not earlier.isalpha():
                continue
            after = rest[mark.end() :]
            if _FIELD_LEAD.match(after) or re.match(r"[A-Z]", after):
                cut = mark.end()
                break
        if cut is None:
            return None
        pos += lead.end() + cut
        if not _FIELD_LEAD.match(text[pos:]):
            return pos
    return None


def _citation_body(text: str) -> tuple[str, int | None]:
    """Return the citation prose and the index where field labels must stop.

    "Citation:" is the normal label. A bare "Citation" before the prose is
    the same label without a colon ("Citation 2d Lt. Murphy…"), and the index
    also misspells that label. When the word is dropped into a citation that
    already started ("Citation Shortly…") or introduces a note
    ("Citation represents…"), it is not a field boundary.
    """
    bare = _CITATION_LABEL_RE.search(text)
    if bare and bare.group(0).lower().startswith("citation") and text[bare.end() - 1 : bare.end()] == ":":
        return text[bare.end() :], bare.start()
    if bare:
        before, after = text[: bare.start()], text[bare.end() :]
        if re.match(r"\s*represents\b", after, flags=re.I):
            return before, bare.start()
        if len(before) > 180 and re.search(r"gallantry|intrepidity", before, flags=re.I):
            return f"{before} {after}", None
        return after, bare.start()
    gallantry = re.search(r"\bFor conspicuous gallantry\b", text, flags=re.I)
    if gallantry and gallantry.start() > 40:
        return text[gallantry.start() :], gallantry.start()
    narrative = _narrative_offset(text)
    if narrative:
        return text[narrative:], narrative
    return text, None


def parse_labeled_block(text: str) -> dict:
    text = squash(text)
    citation, citation_at = _citation_body(text)
    matches = [
        match
        for match in LABEL_RE.finditer(text)
        if citation_at is None or match.start() < citation_at
    ]
    fields: dict[str, str] = {}
    # When the citation is the whole entry, labels still describe the header
    # only if they sit in front of a citation label. Otherwise leave them in the prose.
    if citation_at is None:
        matches = []
    for i, match in enumerate(matches):
        key = _label_key(match)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else citation_at
        value = squash(text[start:end]).strip(" ;")
        fields[key] = value
    citation = _strip_citation_trailer(citation)
    return {"citation": citation, "fields": fields}


def restore_collapsed_day_ranges(text: str) -> str:
    """Turn a dropped hyphen in '1213 November 1942' back into '12-13 November 1942'.

    A following year is required when the four digits could themselves be a year,
    so '19-20 February 1944' is recovered and a bare year is left alone.
    """

    def repl(match: re.Match) -> str:
        num, month, year = match.group(1), match.group(2), match.group(3)
        if len(num) != 4:
            return match.group(0)
        d1, d2 = int(num[:2]), int(num[2:])
        if not (1 <= d1 <= 31 and 1 <= d2 <= 31 and d1 < d2):
            return match.group(0)
        looks_like_year = num.startswith(("18", "19", "20"))
        if looks_like_year and not year:
            return match.group(0)
        if looks_like_year and year and num == year:
            return match.group(0)
        tail = f" {year}" if year else ""
        return f"{d1}-{d2} {month}{tail}"

    return re.sub(
        rf"\b(\d{{4}})\s+({DATE_TOKEN})\b(?:\s+((?:18|19|20)\d{{2}})\b)?",
        repl,
        text,
        flags=re.I,
    )


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


def _span_from_match(pattern: re.Pattern, match: re.Match) -> tuple[str, str] | None:
    groups = match.groups()
    try:
        if pattern is DATE_PATTERNS[0] or pattern is DATE_PATTERNS[1]:
            d1, d2, month, year = groups
            start = _iso(int(year), _month_num(month), int(d1))
            end = _iso(int(year), _month_num(month), int(d2))
        elif pattern is DATE_PATTERNS[2]:
            d1, m1, y1, d2, m2, y2 = groups
            start = _iso(int(y1), _month_num(m1), int(d1))
            end = _iso(int(y2), _month_num(m2), int(d2))
        elif pattern is DATE_PATTERNS[3]:
            m1, d1, y1, m2, d2, y2 = groups
            start = _iso(int(y1), _month_num(m1), int(d1))
            end = _iso(int(y2), _month_num(m2), int(d2))
        elif pattern is DATE_PATTERNS[4]:
            month, d1, d2, year = groups
            start = _iso(int(year), _month_num(month), int(d1))
            end = _iso(int(year), _month_num(month), int(d2))
        elif pattern is DATE_PATTERNS[5]:
            d1, d2, month, year = groups
            start = _iso(int(year), _month_num(month), int(d1))
            end = _iso(int(year), _month_num(month), int(d2))
        elif pattern is DATE_PATTERNS[6]:
            day, month, year = groups
            start = _iso(int(year), _month_num(month), int(day))
            end = start
        elif pattern is DATE_PATTERNS[7]:
            month, day, year = groups
            start = _iso(int(year), _month_num(month), int(day))
            end = start
        else:
            month, year = groups
            start = _iso(int(year), _month_num(month), None)
            end = start
    except (ValueError, KeyError):
        return None
    if not start or not end:
        return None
    return start, end


def _cross_month_spans(text: str) -> list[tuple[int, int, str, str, str]]:
    """Spans for '10 May to 14 November 1942'."""
    found = []
    pattern = re.compile(
        rf"(\d{{1,2}})\s+({DATE_TOKEN})\s+to\s+(\d{{1,2}})\s+({DATE_TOKEN})\s+(\d{{4}})",
        re.I,
    )
    for match in pattern.finditer(text):
        d1, m1, d2, m2, year = match.groups()
        try:
            start = _iso(int(year), _month_num(m1), int(d1))
            end = _iso(int(year), _month_num(m2), int(d2))
        except (ValueError, KeyError):
            continue
        if start and end:
            found.append((match.start(), match.end(), start, end, match.group(0)))
    return found


def _tidy_date_label(label: str) -> str:
    return label.replace(" - ", "–").replace(" -", "–")


def _adjacent_date(text: str, cursor: int) -> tuple[int, int, str, str, str] | None:
    """A second date counts only when punctuation separates it from the first.

    "9 October to 19 November 1942, 15 and 23 January 1943" stays one span.
    A later "killed in action as of 2 November 1953" does not.
    """
    gap = re.match(r"\s*(?:,|and)\s*", text[cursor:])
    if not gap:
        return None
    rest = text[cursor + gap.end() :]
    found: tuple[int, int, str, str, str] | None = None
    for pattern in DATE_PATTERNS:
        match = pattern.match(rest)
        if not match:
            continue
        parsed = _span_from_match(pattern, match)
        if not parsed:
            continue
        found = (0, match.end(), parsed[0], parsed[1], match.group(0))
        break
    return found


def parse_date_span(raw: str | None) -> dict:
    """Return start/end ISO dates and a year when a date can be read."""
    result = {"start": None, "end": None, "year": None, "label": None, "matches": []}
    if not raw or blankish(raw):
        return result
    text = squash(raw)
    text = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text, flags=re.I)
    result["label"] = text
    spans = _cross_month_spans(text)
    if not spans:
        for pattern in DATE_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            parsed = _span_from_match(pattern, match)
            if not parsed:
                continue
            spans = [(match.start(), match.end(), parsed[0], parsed[1], match.group(0))]
            break
    if not spans:
        year_only = re.search(r"\b(18|19|20)\d{2}\b", text)
        if year_only:
            result["year"] = int(year_only.group(0))
        return result
    spans.sort()
    first = spans[0]
    chosen = [first]
    extra = _adjacent_date(text, first[1])
    if extra:
        chosen.append((first[1], first[1] + extra[1], extra[2], extra[3], extra[4]))
    result["start"] = min(item[2] for item in chosen)
    result["end"] = max(item[3] for item in chosen)
    result["year"] = int(result["start"][:4])
    result["matches"] = [item[4] for item in chosen]
    result["label"] = ", ".join(_tidy_date_label(item) for item in result["matches"])
    return result


def split_place_and_date(raw: str | None) -> tuple[str | None, dict]:
    if not raw or blankish(raw):
        return None, parse_date_span(None)
    text = squash(raw)
    dates = parse_date_span(text)
    place = text
    if dates["start"]:
        for label in dates.get("matches") or []:
            if label and label in place:
                place = place.replace(label, " ")
    else:
        # No month-and-day date. The previous parser cleared the line so a
        # bare year or "Winter of 1872" was not stored as a place.
        place = ""
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


def _service_in_closing(citation: str | None) -> str | None:
    """The service named in the citation's closing sentence.

    A passing mention of another service ("Air Force gunship", "Navy corpsman")
    is not the recipient's branch. The closing credit line is.
    """
    if not citation:
        return None
    tail = citation[-400:].lower()
    if "tradition" not in tail and "reflect" not in tail and "naval service" not in tail:
        return None
    if "marine corps" in tail:
        return "U.S. Marine Corps"
    if re.search(r"\bair force\b", tail) and "army air" not in tail:
        return "U.S. Air Force"
    if re.search(r"\bunited states navy\b", tail) and "marine corps" not in tail:
        return "U.S. Navy"
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
    closing = _service_in_closing(citation)
    if closing:
        return closing
    if citation:
        # Do not treat a passing mention of naval gunfire as a Navy award.
        head = re.sub(r"\bnaval gunfire\b", " ", citation[:500], flags=re.I)
        found = _branch_in(head)
        if found:
            return found
    return "U.S. Army"


def citation_implies_death(citation: str | None) -> bool:
    """True when the citation says the recipient died.

    A mention that someone else was mortally wounded, or that enemies were
    killed in action, does not make the award posthumous.
    """
    if not citation:
        return False
    low = citation.lower()
    if any(phrase in low for phrase in RECIPIENT_DEATH_PHRASES):
        return True
    # "lost his life" counts unless the sentence is about a person who was saved.
    if "lost his life" in low or "lost her life" in low:
        if "would have lost his life" in low or "would have lost her life" in low:
            return False
        return True
    return False


def tidy_place(place: str | None) -> str | None:
    """Drop leftover date fragments from a place string."""
    if not place:
        return None
    text = re.split(
        r"\b(?:entered service|accredited to|appointed from)\b",
        place,
        maxsplit=1,
        flags=re.I,
    )[0]
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
        if word.upper() == "USS":
            return "USS"
        if word.isupper() and len(word) > 2:
            return word.capitalize()
        return word

    return " ".join(fix(w) for w in text.split())


_SHIP_STOP = {
    "a", "an", "after", "and", "as", "at", "but", "by", "capt", "captain",
    "carrying", "colonel", "commander", "corporal", "during", "for", "from",
    "he", "her", "his", "in", "into", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october", "november",
    "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sept", "sep",
    "oct", "nov", "dec", "lieutenant", "lt", "major", "near", "of", "off", "on",
    "over", "private", "sergeant", "sgt", "she", "st", "that", "the", "then",
    "this", "to", "undaunted", "under", "was", "were", "when", "where", "which",
    "while", "who", "with",
}


def ship_from_text(text: str | None, last_name: str | None = None) -> str | None:
    """Read a ship name, including two- and three-word names such as San Francisco."""
    if not text:
        return None
    match = re.search(r"\bU\.?\s*S\.?\s*S\.?\s+", text)
    if not match:
        return None
    rest = text[match.end():]
    words: list[str] = []
    for part in re.finditer(r"[A-Za-z][A-Za-z0-9'’.-]*", rest):
        gap = rest[: part.start()]
        # A comma or a sentence break ends the ship name: "U.S.S. Signal, Red River".
        if words and re.search(r"[,.;:!?]", gap):
            break
        bare = part.group(0).strip(".")
        if not bare:
            continue
        low = bare.lower()
        if words and low in _SHIP_STOP:
            break
        if words and last_name and low == last_name.lower():
            break
        if words and low in {"de", "la", "da", "di", "du", "van", "von"}:
            words.append(bare)
            continue
        if words and not bare[0].isupper():
            break
        words.append(bare)
        if len(words) == 4:
            break
    while words and words[-1].lower() in {"de", "la", "da", "di", "du", "van", "von"}:
        words.pop()
    if not words:
        return None
    return "USS " + " ".join(words)


_RANK_PERIOD_RE = re.compile(
    r"\b((?:[A-Z]/)?(?:1st\s+)?)"
    r"(Private First Class|Lance Corporal|First Sergeant|Staff Sergeant|Technical Sergeant|"
    r"Master Sergeant|Gunnery Sergeant|Sergeant Major|Platoon Sergeant|"
    r"Second Lieutenant|First Lieutenant|Lieutenant Colonel|Lieutenant Commander|"
    r"Lieutenant|Sergeant|Corporal|Captain|Major|Colonel|General|Admiral|Commander|"
    r"Private|Seaman)"
    r"\.(?=\s+[A-Z])",
)

_BLEED_NAME_RE = re.compile(
    r"(?<=[.?!]\s)[A-Z]{3,}(?:\s+[A-Z]{3,})?,\s+[A-Z]{2,}(?:\s+[A-Z]\.?)?\b"
)


def fix_ocr_years(text: str) -> str:
    """Turn a leading or trailing i/l that stands in for the digit 1 back into a year."""

    def lead(match: re.Match) -> str:
        year = "1" + match.group(1)
        if year.startswith(("18", "19")):
            return year
        return match.group(0)

    def trail(match: re.Match) -> str:
        year = match.group(1) + "1"
        if year.startswith(("18", "19")) and 1800 <= int(year) <= 1999:
            return year
        return match.group(0)

    text = re.sub(r"(?<![A-Za-z0-9])[ilI](\d{3})\b", lead, text)
    text = re.sub(r"\b((?:18|19)\d)[ilI]\b", trail, text)
    return text


def fix_underscores(text: str) -> str:
    """Underscores in the index are spaces, or hyphens between numbers."""
    text = re.sub(r"(\d)_(\d)", r"\1-\2", text)
    text = text.replace("_", " ")
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r" {2,}", " ", text)
    return text


def fix_rank_periods(text: str) -> str:
    """Drop the period left behind when a rank abbreviation was expanded."""
    return _RANK_PERIOD_RE.sub(r"\1\2", text)


def truncate_entry_bleed(text: str) -> str:
    """Cut a citation that runs into the next recipient's index entry."""
    if not text:
        return text
    cut: int | None = None
    ranks = list(re.finditer(r"Rank and organization", text, flags=re.I))
    if len(ranks) >= 2:
        cut = ranks[1].start()
    for match in _BLEED_NAME_RE.finditer(text):
        if match.start() < 80:
            continue
        window = text[match.end() : match.end() + 80]
        if not re.search(r"Rank and organization|Place and date|Born:|G\.O\. No", window, flags=re.I):
            continue
        cut = match.start() if cut is None else min(cut, match.start())
    if cut is None:
        return text
    head = text[:cut]
    head = re.sub(
        r"\s+[A-Z]{3,}(?:\s+[A-Z]{3,})?,\s+[A-Z]{2,}(?:\s+[A-Z]\.?)?\s*$",
        "",
        head,
    )
    return head.strip()


def prepare_entry_text(text: str) -> str:
    text = fix_ocr_years(text or "")
    text = fix_underscores(text)
    text = truncate_entry_bleed(text)
    return text


def polish_prose(text: str) -> str:
    text = fix_rank_periods(text or "")
    text = fix_underscores(text)
    text = fix_ocr_years(text)
    return squash(text)
