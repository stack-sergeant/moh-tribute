"""Build records for recipients the Army-index parser dropped.

The citation text is taken from the public-domain snapshots in
data/raw/army/. Nothing here copies prose from the Congressional
Medal of Honor Society. CMOHS pages are linked as references, and
the posthumous flag was checked on those pages.

Run from the repository root:

    python3 scripts/extract_cmohs_gap.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mohlib import (
    detect_branch,
    find_state,
    format_indexed_name,
    name_identity,
    parse_date_span,
    parse_labeled_block,
    slugify,
    split_place_and_date,
    squash,
    tidy_place,
)
from parse_army import CAMPAIGNS, RANK_RE, html_to_text

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "army"
OUT = ROOT / "data" / "cmohs-gap-additions.json"

# file, marker, how the name is tagged, CMOHS slug, posthumous checked on CMOHS
# Still absent after the citation-index parser fixes on main.
INDEX_GAPS = [
    ("citations1.html", "BOURKE, JOHN G.", "p", "john-g-bourke", False),
    ("citations1.html", "DE LACEY, PATRICK", "p", "patrick-delacey", False),
    ("citations1.html", "JAMES, ISAAC", "p", "isaac-james", False),
    ("citations1.html", "BROWN, JAMES", "p", "james-brown", False),
    ("citations2.html", "MURPHY, JOHN P.", "p", "john-p-murphy", False),
    ("citations3.html", "JIM", "h3", "jim", False),
    ("citations3.html", "NOLAN, RICHARD J.", "h3", "richard-j-nolan", False),
    ("citations3.html", "RAGNAR, THEODORE", "h3", "theodore-ragnar", False),
    ("citations3.html", "TOY, FREDERICK E.", "h3", "frederick-e-toy", False),
    ("citations3.html", "WILSON, WILLIAM O.", "h3", "william-o-wilson", False),
    ("citations3.html", "HOLLAND, DAVID", "p", "david-holland", False),
    ("citations7.html", "OLSEN, ANTON", "p", "anton-olsen", False),
]

CMOHS = "https://www.cmohs.org/recipients/"


def fix_labels(text: str) -> str:
    text = re.sub(r"\bCita\s+tion\b", "Citation", text, flags=re.I)
    text = re.sub(r"\bCitat(?:at)?ion\b", "Citation", text, flags=re.I)
    text = re.sub(r"\bCitatlon\b", "Citation", text, flags=re.I)
    text = re.sub(r"\bCitatian\b", "Citation", text, flags=re.I)
    text = re.sub(r"\bCitarion\b", "Citation", text, flags=re.I)
    text = re.sub(r"\bCltatlon\b", "Citation", text, flags=re.I)
    text = re.sub(r"\bCltation\b", "Citation", text, flags=re.I)
    return text


def clean_citation(citation: str) -> str:
    citation = fix_labels(citation)
    if re.match(r"^(?:Y\.\s*)?Date of issue\b", citation, flags=re.I) or re.match(
        r"^Citation\b", citation, flags=re.I
    ):
        citation = re.sub(r"^.*?\bCitation\s*[:.]?\s*", "", citation, count=1, flags=re.I)
    return squash(citation)


def body_for(html: str, marker: str, kind: str) -> str:
    if kind == "p":
        pattern = rf"(?is)<p>\s*{re.escape(marker)}\s*</p>\s*<p>(.*?)</p>"
    else:
        pattern = rf"(?is)<h3>\s*{re.escape(marker)}\s*</h3>(.*?)(?=<h[123]\b)"
    match = re.search(pattern, html)
    if not match:
        raise SystemExit(f"block not found: {marker}")
    return html_to_text(match.group(1)) if kind == "h3" else squash(re.sub(r"(?is)<[^>]+>", " ", match.group(1)))


def record_from_index(file_name: str, marker: str, kind: str, slug: str, posthumous: bool) -> dict:
    html = (RAW / file_name).read_text(encoding="utf-8", errors="replace")
    text = fix_labels(body_for(html, marker, kind))
    parsed = parse_labeled_block(text)
    fields = parsed["fields"]
    citation = clean_citation(parsed["citation"])
    if len(citation) < 12:
        # Some index entries print the citation without a label.
        for splitter in (
            r"G\.O\. No\.[^.]*\.\s*",
            r"Date and place of birth:[^.]*\.\s*",
            r"Birth:[^.]*\.\s*",
        ):
            tail = re.split(splitter, text, maxsplit=1, flags=re.I)
            if len(tail) == 2 and len(squash(tail[1])) > 40:
                citation = clean_citation(tail[1])
                break
    if len(citation) < 12:
        conspicuous = re.search(r"For conspicuous gallantry\b.*", text, flags=re.I)
        if conspicuous and len(conspicuous.group(0)) > 40:
            citation = clean_citation(conspicuous.group(0))
    if len(citation) < 6:
        raise SystemExit(f"short citation for {marker}: {citation!r} from {text[:240]!r}")
    name_raw = marker.lstrip("*").strip()
    if name_raw == "JIM":
        parts = {
            "display": "Jim",
            "sort": "Jim",
            "last": "Jim",
            "first": "",
            "middle": "",
            "suffix": "",
        }
    else:
        parts = format_indexed_name(name_raw)
    rank_org = fields.get("rank and organization") or fields.get("rank") or ""
    rank = ""
    unit = ""
    if rank_org:
        bits = [bit.strip() for bit in rank_org.split(",")]
        rank = bits[0]
        if "." in rank:
            head = rank.split(".")[0].strip()
            if RANK_RE.fullmatch(head):
                rank = head
        unit = ", ".join(bits[1:]).strip(" .")
    place_raw, dates = split_place_and_date(fields.get("place and date") or fields.get("place"))
    if not dates.get("start") and fields.get("date"):
        dates = parse_date_span(fields.get("date"))
        if not place_raw:
            place_raw = fields.get("place")
    if not dates.get("year"):
        # Prefer the action date inside the citation over an issue date earlier in the entry.
        dates = parse_date_span(citation) or dates
    place = tidy_place(place_raw)
    if (place and re.search(r"sioux campaign", place, flags=re.I)) or (
        not place and dates.get("label") and re.search(r"sioux campaign", str(dates.get("label")), flags=re.I)
    ):
        place = "Sioux Campaign"
        dates = {"start": None, "end": None, "label": "1890", "year": 1890}
    if not place and re.search(r"Fort De Russy", citation):
        place = "Fort De Russy, Red River"
    if not place and re.search(r"Cienfuegos, Cuba", citation):
        place = "Cienfuegos, Cuba"
    if re.search(r"U\.S\.S\. Marblehead", citation) and (not unit or unit == "U.S. Navy"):
        unit = "U.S.S. Marblehead"
    if re.search(r"U\.S\.S\. Albatross", citation) and (not unit or unit == "U.S. Navy"):
        unit = "U.S.S. Albatross"
    birth = fields.get("birth") or fields.get("born") or ""
    entered = fields.get("entered service at") or fields.get("entered service") or ""
    accredited = fields.get("accredited to") or ""
    home_state = find_state(accredited) or find_state(entered) or find_state(birth)
    birth_year = parse_date_span(birth).get("year")
    conflict, era = CAMPAIGNS[file_name]
    branch = detect_branch(rank_org, citation)
    award_id = slugify(f"{parts['display']}-{dates.get('year') or 'undated'}-{place_raw or conflict}")
    return {
        "awardId": award_id,
        "indexedName": name_raw,
        "name": parts["display"],
        "nameSort": parts["sort"],
        "last": parts["last"],
        "first": parts["first"],
        "middle": parts["middle"],
        "suffix": parts["suffix"],
        "identity": name_identity(parts),
        "rank": rank or None,
        "unit": unit or None,
        "rankAndOrganization": rank_org or None,
        "branch": branch,
        "conflict": conflict,
        "era": era,
        "actionPlace": place,
        "actionPlaceRaw": place_raw,
        "actionDate": dates.get("start"),
        "actionDateEnd": dates.get("end"),
        "actionDateLabel": dates.get("label"),
        "actionYear": dates.get("year"),
        "posthumous": posthumous,
        "posthumousMarked": posthumous,
        "citation": citation,
        "enteredServiceAt": None if not entered else squash(entered),
        "birth": None if not birth else squash(birth),
        "birthYear": birth_year,
        "accreditedTo": None if not accredited else squash(accredited),
        "homeState": home_state,
        "issueDate": fields.get("date of issue") or fields.get("issue date"),
        "generalOrder": fields.get("g.o. no."),
        "sourceUrl": f"https://www.army.mil/medalofhonor/{file_name}",
        "sourceLabel": "U.S. Army Medal of Honor citation index",
        "extraSources": [CMOHS + slug],
        "nameNotes": [
            "The Army citation index prints this entry, and the site parser had dropped it. "
            "Awarded posthumously was checked on the Congressional Medal of Honor Society page listed with the sources. "
            "That page is a reference only. Its prose is not copied here."
        ],
        "continuesPerson": False,
        "campaignFile": file_name,
    }


def blank(value: str | None) -> str | None:
    if not value:
        return None
    text = squash(value).strip(" .")
    return text or None


def main() -> None:
    records = []
    for file_name, marker, kind, slug, posthumous in INDEX_GAPS:
        record = record_from_index(file_name, marker, kind, slug, posthumous)
        record["issueDate"] = blank(record.get("issueDate"))
        record["generalOrder"] = blank(record.get("generalOrder"))
        records.append(record)
        print(
            f"{record['name']}|{record['branch']}|{record['conflict']}|{record['actionYear']}|"
            f"{record['posthumous']}|{record['citation'][:70]}"
        )
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} -> {OUT}")


if __name__ == "__main__":
    main()
