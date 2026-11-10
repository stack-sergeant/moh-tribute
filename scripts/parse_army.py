"""Parse the U.S. Army Medal of Honor citation index into award records.

Source pages are the public-domain compilations at
https://www.army.mil/medalofhonor/recipients.html
Snapshots live in data/raw/army/ because some clients are blocked by the
live site. See scripts/download_citations.py to refresh them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from mohlib import (
    blankish,
    citation_implies_death,
    detect_branch,
    tidy_place,
    find_state,
    format_indexed_name,
    name_identity,
    parse_date_span,
    parse_labeled_block,
    ship_from_text,
    slugify,
    split_place_and_date,
    squash,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "army"

# Campaign labels follow the Army index. Era is the rolled-up grouping
# used on the homepage so no single war is the visual center.
CAMPAIGNS = {
    "citations1.html": ("Civil War", "Civil War"),
    "citations2.html": ("Civil War", "Civil War"),
    "citations3.html": ("Indian Wars", "Indian Wars"),
    "citations4.html": ("Peacetime and interim", "Peacetime and other actions"),
    "citations5.html": ("Korean Expedition", "Expeditions, 1871–1933"),
    "citations6.html": ("Peacetime and interim", "Peacetime and other actions"),
    "citations7.html": ("Spanish–American War", "Expeditions, 1871–1933"),
    "citations8.html": ("Philippine–American War", "Expeditions, 1871–1933"),
    "citations9.html": ("Boxer Rebellion", "Expeditions, 1871–1933"),
    "citations10.html": ("Peacetime and interim", "Peacetime and other actions"),
    "citations11.html": ("Philippine–American War", "Expeditions, 1871–1933"),
    "citations12.html": ("Veracruz occupation", "Expeditions, 1871–1933"),
    "citations13.html": ("Haitian Campaign", "Expeditions, 1871–1933"),
    "citations14.html": ("Peacetime and interim", "Peacetime and other actions"),
    "citations15.html": ("Dominican Campaign", "Expeditions, 1871–1933"),
    "citations16.html": ("World War I", "World War I"),
    "citations17.html": ("Haitian Campaign", "Expeditions, 1871–1933"),
    "citations18.html": ("Nicaraguan Campaign", "Expeditions, 1871–1933"),
    "citations19.html": ("Peacetime and interim", "Peacetime and other actions"),
    "citations20.html": ("World War II", "World War II"),
    "citations21.html": ("World War II", "World War II"),
    "citations22.html": ("World War II", "World War II"),
    "citations23.html": ("World War II", "World War II"),
    "citations24.html": ("Korean War", "Korean War"),
    "citations25.html": ("Vietnam War", "Vietnam War"),
    "citations26.html": ("Vietnam War", "Vietnam War"),
    "citations27.html": ("Somalia", "Since 1975"),
    "citations28.html": ("Special acts of Congress", "Peacetime and other actions"),
    "citations29.html": ("Iraq War", "Since 1975"),
    "citations30.html": ("War in Afghanistan", "Since 1975"),
    "citations31.html": ("Operation Inherent Resolve", "Since 1975"),
    "citations32.html": ("War in Afghanistan", "Since 1975"),
}

SKIP_NAME = re.compile(
    r"^(additional medal of honor resources|[a-z]|index)$",
    re.I,
)

RANK_RE = re.compile(
    r"\b(Chief Warrant Officer Five|Chief Warrant Officer Four|Chief Warrant Officer|"
    r"Warrant Officer|Command Sergeant Major|Sergeant Major|Platoon Sergeant|"
    r"Master Gunnery Sergeant|Gunnery Sergeant|First Sergeant|Master Sergeant|"
    r"Sergeant First Class|Technical Sergeant|Staff Sergeant|Technician Fifth Grade|"
    r"Technician Fourth Grade|Lance Corporal|Private First Class|"
    r"Specialist Six|Specialist Five|Specialist Four|Specialist|"
    r"Petty Officer First Class|Petty Officer Second Class|Petty Officer Third Class|"
    r"Hospital Corpsman|Pharmacist's Mate First Class|Pharmacist's Mate|"
    r"Lieutenant General|Major General|Brigadier General|Lieutenant Colonel|"
    r"Lieutenant Commander|Rear Admiral|Vice Admiral|"
    r"First Lieutenant|Second Lieutenant|Lieutenant|Commander|Colonel|Captain|Major|"
    r"General|Admiral|Sergeant|Corporal|Private|Seaman)\b"
)

CITATION_PLACE_RE = re.compile(
    r"\b(?:in|near|at|outside)\s+(?:the\s+)?(?:town of\s+|vicinity of\s+|city of\s+|village of\s+)?"
    r"([A-Z][A-Za-z0-9 .'’\-]{2,90}?),\s*"
    r"(Iraq|Afghanistan|Somalia|Republic of Vietnam|South Vietnam|Vietnam|"
    r"North Korea|South Korea|Korea|France|Germany|Belgium|Italy|Japan|"
    r"the Philippines|Philippines|China|Cuba|Mexico|Haiti|Nicaragua)\b"
)


US_STATES = (
    "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|"
    "District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|"
    "Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|"
    "Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|"
    "New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|"
    "Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|"
    "Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming"
)

STATE_PLACE_RE = re.compile(
    rf"\b(?:at|near|in)\s+([A-Z][A-Za-z0-9 .'’\-]{{2,50}}?),\s+({US_STATES})\b"
)
SIMPLE_PLACE_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9 .'’\-]{2,40}),\s+"
    r"(Iraq|Afghanistan|Somalia|Korea|Vietnam|France|Germany|Japan|Italy|Belgium|Philippines)\b"
)


def infer_conflict(year: int, citation: str | None, place: str | None, conflict: str, era: str):
    """Reassign a second award that the index filed under a different war."""
    windows = {
        "Civil War": (1861, 1865),
        "World War I": (1917, 1918),
        "World War II": (1941, 1945),
        "Korean War": (1950, 1953),
        "Vietnam War": (1959, 1975),
        "Indian Wars": (1866, 1898),
    }
    span = windows.get(conflict)
    if span is None or span[0] <= year <= span[1]:
        return conflict, era
    text = f"{citation or ''} {place or ''}".lower()
    if 1861 <= year <= 1865:
        return "Civil War", "Civil War"
    if 1917 <= year <= 1918:
        return "World War I", "World War I"
    if 1941 <= year <= 1945:
        return "World War II", "World War II"
    if 1950 <= year <= 1953:
        return "Korean War", "Korean War"
    if 1965 <= year <= 1973:
        return "Vietnam War", "Vietnam War"
    if "indian" in text or 1866 <= year <= 1891:
        return "Indian Wars", "Indian Wars"
    return conflict, era


def place_from_citation(citation: str) -> str | None:
    if not citation:
        return None
    for pattern in (CITATION_PLACE_RE, STATE_PLACE_RE, SIMPLE_PLACE_RE):
        match = pattern.search(citation)
        if not match:
            continue
        locality = squash(match.group(1)).strip(" ,")
        if len(locality) > 80 or " while " in locality.lower():
            continue
        place = tidy_place(f"{locality}, {match.group(2)}")
        if place:
            return place
    return None


def rank_from_citation(citation: str) -> str | None:
    match = RANK_RE.search(citation or "")
    if not match:
        return None
    # Ignore a rank that shows up only late in a long citation.
    if match.start() > 900:
        return None
    return match.group(1)


def html_to_text(fragment: str) -> str:
    fragment = re.sub(r"(?is)<script[\s\S]*?</script>", " ", fragment)
    fragment = re.sub(r"(?is)<style[\s\S]*?</style>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", " ", fragment)
    fragment = re.sub(r"(?i)</p>", " ", fragment)
    fragment = re.sub(r"(?is)<[^>]+>", " ", fragment)
    return squash(fragment)


def extra_links(fragment: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]+)"', fragment, flags=re.I)
    cleaned = []
    for href in hrefs:
        if href.startswith("//"):
            href = "https:" + href
        if href.startswith("/"):
            href = "https://www.army.mil" + href
        if not href.startswith("http"):
            continue
        if any(host in href for host in ("army.mil", "defense.gov", "navy.mil", "marines.mil", "af.mil")):
            cleaned.append(href.split("?")[0])
    # Preserve order, drop duplicates.
    seen = set()
    out = []
    for href in cleaned:
        if href not in seen:
            seen.add(href)
            out.append(href)
    return out


def parse_file(path: Path) -> list[dict]:
    conflict, era = CAMPAIGNS[path.name]
    html = path.read_text(encoding="utf-8", errors="replace")
    html = re.sub(r"(?is)<script[\s\S]*?</script>", " ", html)
    parts = re.split(r"(?i)<h3[^>]*>", html)
    awards = []
    for part in parts[1:]:
        if "</h3>" not in part.lower():
            continue
        name_html, rest = re.split(r"(?i)</h3>", part, maxsplit=1)
        name_raw = squash(re.sub(r"(?is)<[^>]+>", " ", name_html))
        if not name_raw or SKIP_NAME.match(name_raw.strip(" *")):
            continue
        continuation = bool(re.fullmatch(r"\*?second award", name_raw.strip(), flags=re.I))
        if not continuation and "," not in name_raw and len(name_raw) < 4:
            continue
        if continuation and not awards:
            continue
        posthumous_mark = name_raw.strip().startswith("*")
        notes = re.findall(r"\(([^)]*)\)", name_raw)
        name_for_parse = re.sub(r"\([^)]*\)", " ", name_raw)
        if continuation:
            parts_name = {
                "display": awards[-1]["name"],
                "sort": awards[-1]["nameSort"],
                "last": awards[-1]["last"],
                "first": awards[-1]["first"],
                "middle": awards[-1]["middle"],
                "suffix": awards[-1]["suffix"],
            }
            # A second award keeps the person's identity and fills gaps from the first.
            inherited = awards[-1]
        else:
            parts_name = format_indexed_name(name_for_parse)
            inherited = None
        if not parts_name["display"] or len(parts_name["display"]) < 3:
            continue
        text = html_to_text(rest.split("<h2")[0].split("<h1")[0])
        # Stop before the resources footer if it was pulled into the last entry.
        text = re.split(r"Additional Medal of Honor Resources", text, maxsplit=1)[0]
        parsed = parse_labeled_block(text)
        fields = parsed["fields"]
        citation = parsed["citation"]
        if not citation or len(citation) < 12:
            continue
        rank_org = fields.get("rank and organization", "")
        rank = ""
        unit = ""
        if rank_org:
            bits = [b.strip() for b in rank_org.split(",")]
            rank = bits[0]
            if "." in rank:
                head = rank.split(".")[0].strip()
                if RANK_RE.fullmatch(head):
                    rank = head
            unit = ", ".join(bits[1:]).strip(" .")
        place_raw, dates = split_place_and_date(fields.get("place and date"))
        if dates["start"] is None:
            dating = re.sub(r"March\s+3(?:rd)?,\s*1863", " ", citation or "", flags=re.I)
            dating = re.sub(r"\b3\s+March\s+1863\b", " ", dating, flags=re.I)
            fallback = parse_date_span(dating)
            if fallback["start"]:
                dates = fallback
        place = tidy_place(place_raw)
        if not place:
            place = place_from_citation(citation)
        if not place and re.search(r"\bIwo Jima\b", citation or ""):
            place = "Iwo Jima"
        if not place:
            place = ship_from_text(rank_org) or ship_from_text(citation)
        if not rank:
            rank = rank_from_citation(citation) or ""
        birth = fields.get("birth") or fields.get("born") or ""
        entered = fields.get("entered service at") or ""
        accredited = fields.get("accredited to") or ""
        home_state = find_state(accredited) or find_state(entered) or find_state(birth)
        birth_year = None
        birth_date = parse_date_span(birth)
        if birth_date["year"]:
            birth_year = birth_date["year"]
        else:
            year_match = re.search(r"\b(18|19|20)\d{2}\b", birth)
            if year_match:
                birth_year = int(year_match.group(0))
        award_conflict, award_era = conflict, era
        branch = detect_branch(rank_org, citation)
        if inherited:
            rank = rank or inherited["rank"] or ""
            unit = unit or inherited["unit"] or ""
            branch = branch if rank_org or re.search(r"marine corps|naval service|united states", citation or "", re.I) else inherited["branch"]
            if not home_state:
                home_state = inherited["homeState"]
            if not birth or blankish(birth):
                birth = inherited["birth"] or ""
                birth_year = inherited["birthYear"]
            if not entered:
                entered = inherited["enteredServiceAt"] or ""
        # A second award printed under another war's alphabetical list is reassigned by date.
        if continuation and dates["year"]:
            award_conflict, award_era = infer_conflict(dates["year"], citation, place, conflict, era)
        if re.search(r"medal of honor|second medal|awarded to unknowns", parts_name["display"], re.I):
            continue
        posthumous = bool(posthumous_mark or citation_implies_death(citation))
        source_url = f"https://www.army.mil/medalofhonor/{path.name}"
        award_id = slugify(
            f"{parts_name['display']}-{dates['year'] or 'undated'}-{place_raw or conflict}"
        )
        awards.append(
            {
                "awardId": award_id,
                "indexedName": squash(name_raw).lstrip("*").strip(),
                "name": parts_name["display"],
                "nameSort": parts_name["sort"],
                "last": parts_name["last"],
                "first": parts_name["first"],
                "middle": parts_name["middle"],
                "suffix": parts_name["suffix"],
                "identity": name_identity(parts_name),
                "rank": rank or None,
                "unit": unit or None,
                "rankAndOrganization": rank_org or None,
                "branch": branch,
                "conflict": award_conflict,
                "era": award_era,
                "actionPlace": place,
                "actionPlaceRaw": place_raw,
                "actionDate": dates["start"],
                "actionDateEnd": dates["end"],
                "actionDateLabel": dates["label"],
                "actionYear": dates["year"],
                "posthumous": posthumous,
                "posthumousMarked": posthumous_mark,
                "citation": citation,
                "enteredServiceAt": None if blankish(entered) else squash(entered),
                "birth": None if blankish(birth) else squash(birth),
                "birthYear": birth_year,
                "accreditedTo": None if blankish(accredited) else squash(accredited),
                "homeState": home_state,
                "issueDate": None if blankish(fields.get("date of issue")) else fields.get("date of issue"),
                "generalOrder": None if blankish(fields.get("g.o. no.")) else fields.get("g.o. no."),
                "sourceUrl": source_url,
                "nameNotes": [squash(n) for n in notes],
                "continuesPerson": continuation,
                "sourceLabel": "U.S. Army Medal of Honor citation index",
                "extraSources": extra_links(rest[:2500]),
                "campaignFile": path.name,
            }
        )
    return awards


def load_army_awards() -> list[dict]:
    awards: list[dict] = []
    missing = []
    for filename in CAMPAIGNS:
        path = RAW / filename
        if not path.exists():
            missing.append(filename)
            continue
        awards.extend(parse_file(path))
    if missing:
        raise SystemExit(f"Missing citation snapshots: {', '.join(missing)}")
    # Disambiguate award ids.
    seen: dict[str, int] = {}
    for award in awards:
        base = award["awardId"]
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            award["awardId"] = f"{base}-{seen[base]}"
    return awards


def main() -> None:
    awards = load_army_awards()
    out = ROOT / "data" / "awards-army.json"
    out.write_text(json.dumps(awards, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"awards {len(awards)} -> {out}")


if __name__ == "__main__":
    main()
