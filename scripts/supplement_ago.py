"""Add Medal of Honor awards that post-date the Army citation-index snapshots.

The Army Publishing Directorate general orders are public-domain U.S.
government documents. This script downloads only orders whose recipient
is not already in the parsed citation index.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from mohlib import (
    citation_implies_death,
    detect_branch,
    find_state,
    format_indexed_name,
    name_identity,
    parse_date_span,
    slugify,
    squash,
)
from parse_army import RANK_RE, infer_conflict, place_from_citation, rank_from_citation

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ago"
INDEX_URL = "https://armypubs.army.mil/ProductMaps/PubForm/AGO.aspx"
UA = "ValorRecordDataPipeline/1.0 (educational archive of public-domain citations)"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read().decode("utf-8", "replace")


def ago_orders(html: str) -> list[dict]:
    orders = []
    for match in re.finditer(
        r'href="Details\.aspx\?PUB_ID=(\d+)"[^>]*>\s*(AGO [^<]+)</a>\s*</td>\s*<td>[^<]*</td>\s*<td>[^<]*</td>\s*<td>([^<]*MEDAL OF HONOR[^<]*)</td>',
        html,
        flags=re.I,
    ):
        orders.append(
            {
                "pubId": match.group(1),
                "number": squash(match.group(2)),
                "title": squash(match.group(3)),
            }
        )
    return orders


def title_name(title: str) -> str | None:
    title = re.sub(r"\bTEH\b", "THE", title, flags=re.I)
    title = re.sub(r"\bGERGEANT\b", "SERGEANT", title, flags=re.I)
    title = re.sub(r"\bFIRSDT\b", "FIRST", title, flags=re.I)
    title = re.sub(r"\bNESLON\b", "NELSON", title, flags=re.I)
    text = re.sub(r"^AWARD OF THE MEDAL OF HONOR(?:\s+(?:OF|TO|FOR))?\s+", "", title, flags=re.I)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\bCHAPLAIN\b", " ", text, flags=re.I)
    text = squash(text)
    rank_re = re.compile(RANK_RE.pattern, re.I)
    changed = True
    while changed:
        changed = False
        match = rank_re.match(text.strip())
        if match:
            text = text[match.end() :].strip(" ,")
            changed = True
    text = text.strip(" .")
    if not text or len(text.split()) < 2:
        return None
    parts = text.split()
    if parts[0].endswith(","):
        return text
    suffix = ""
    while parts and parts[-1].upper().rstrip(".") in {"JR", "SR", "II", "III", "IV", "2D", "3D"}:
        suffix = parts.pop() 
        # keep the last suffix only; "Jr." is the usual case
        suffix = suffix.rstrip(".")
    if len(parts) < 2:
        return None
    last = parts[-1]
    given = " ".join(parts[:-1])
    indexed = f"{last}, {given}"
    if suffix:
        indexed = f"{indexed}, {suffix}."
    return indexed


def conflict_from_text(text: str, year: int | None) -> tuple[str, str]:
    low = text.lower()
    if "afghanistan" in low or "nuristan" in low or "operation enduring freedom" in low:
        return "War in Afghanistan", "Since 1975"
    if "operation inherent resolve" in low or "hawija" in low:
        return "Operation Inherent Resolve", "Since 1975"
    if "iraq" in low or "operation iraqi freedom" in low:
        return "Iraq War", "Since 1975"
    if "somalia" in low or "mogadishu" in low:
        return "Somalia", "Since 1975"
    if "vietnam" in low:
        return "Vietnam War", "Vietnam War"
    if "korea" in low:
        return "Korean War", "Korean War"
    if "venezuela" in low or "absolute resolve" in low:
        return "Operation Absolute Resolve", "Since 1975"
    if year and 1941 <= year <= 1945:
        return "World War II", "World War II"
    if year and 1950 <= year <= 1953:
        return "Korean War", "Korean War"
    if year and 1964 <= year <= 1973:
        return "Vietnam War", "Vietnam War"
    if year == 1898:
        return "Spanish–American War", "Expeditions, 1871–1933"
    if year and 1861 <= year <= 1865:
        return "Civil War", "Civil War"
    if year and 1866 <= year <= 1891:
        return "Indian Wars", "Indian Wars"
    return "Not classified in the general order", "Peacetime and other actions"


def pdf_text(pdf_path: Path) -> str:
    completed = subprocess.run(
        ["pdftotext", "-raw", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = completed.stdout.replace("\u00ad", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def citation_from_pdf(text: str) -> str:
    match = re.search(r"(For conspicuous gallantry[\s\S]+)", text, flags=re.I)
    body = match.group(1) if match else text
    body = re.split(r"\bBY ORDER OF THE SECRETARY OF THE ARMY\b", body, maxsplit=1, flags=re.I)[0]
    body = re.split(r"\bDISTRIBUTION:\b", body, maxsplit=1, flags=re.I)[0]
    body = squash(body)
    return body


def _close(left: str, right: str) -> bool:
    if left == right:
        return True
    if not left or not right:
        return False
    return difflib.SequenceMatcher(None, left, right).ratio() >= 0.86


def already_have(indexed_name: str, awards: list[dict]) -> bool:
    parts = format_indexed_name(indexed_name)
    ident = name_identity(parts)
    if any(award["identity"] == ident for award in awards):
        return True
    last = slugify(parts["last"])
    first = slugify(parts["first"])
    candidates = set()
    for award in awards:
        if not _close(slugify(award["last"]), last):
            continue
        other = slugify(award["first"])
        if first and other and first[0] != other[0]:
            continue
        if first and other and not _close(first, other) and first != other:
            continue
        candidates.add(award["identity"])
    return len(candidates) == 1


def load_supplements(awards: list[dict]) -> list[dict]:
    RAW.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "data" / "awards-ago.json"
    if os.environ.get("SKIP_AGO_FETCH") == "1" and cache.exists():
        print("using cached general orders")
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        html = fetch(INDEX_URL)
        (RAW / "ago-index.html").write_text(html, encoding="utf-8")
    except Exception as error:
        print("AGO index unavailable:", error)
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))
        return []
    orders = ago_orders(html)
    print(f"AGO medal orders listed: {len(orders)}")
    added = []
    for order in orders:
        indexed = title_name(order["title"])
        if not indexed or already_have(indexed, awards) or already_have(indexed, added):
            continue
        detail_url = f"https://armypubs.army.mil/ProductMaps/PubForm/Details.aspx?PUB_ID={order['pubId']}"
        try:
            detail = fetch(detail_url)
        except Exception as error:
            print(" detail failed", order["number"], error)
            continue
        pdf_match = re.search(r"href='([^']+\.pdf)'", detail)
        if not pdf_match:
            print(" no pdf", order["number"])
            continue
        pdf_url = urljoin(detail_url, pdf_match.group(1))
        dest = RAW / f"{order['number'].replace(' ', '_')}.pdf"
        if not dest.exists() or dest.stat().st_size < 1000:
            downloaded = subprocess.run(
                ["curl", "-fsSL", "-A", UA, "--max-time", "60", "-o", str(dest), pdf_url],
                capture_output=True,
            )
            if downloaded.returncode != 0 or not dest.exists() or dest.stat().st_size < 1000:
                print(" pdf failed", pdf_url, downloaded.stderr[-200:])
                continue
        try:
            text = pdf_text(dest)
        except subprocess.CalledProcessError as error:
            print(" pdftotext failed", dest, error)
            continue
        citation = citation_from_pdf(text)
        if len(citation) < 80:
            print(" short citation", order["number"], len(citation))
            continue
        parts = format_indexed_name(indexed)
        dating = re.sub(r"March\s+3(?:rd)?,\s*1863", " ", citation, flags=re.I)
        dating = re.sub(r"\b3\s+March\s+1863\b", " ", dating, flags=re.I)
        dates = parse_date_span(dating)
        place = place_from_citation(citation)
        conflict, era = conflict_from_text(citation, dates["year"])
        posthumous = "posthumously" in text.lower() or citation_implies_death(citation)
        added.append(
            {
                "awardId": slugify(f"{parts['display']}-{dates['year'] or 'undated'}-ago"),
                "indexedName": indexed,
                "name": parts["display"],
                "nameSort": parts["sort"],
                "last": parts["last"],
                "first": parts["first"],
                "middle": parts["middle"],
                "suffix": parts["suffix"],
                "identity": name_identity(parts),
                "rank": rank_from_citation(citation),
                "unit": None,
                "rankAndOrganization": None,
                "branch": detect_branch(None, citation),
                "conflict": conflict,
                "era": era,
                "actionPlace": place,
                "actionPlaceRaw": place,
                "actionDate": dates["start"],
                "actionDateEnd": dates["end"],
                "actionDateLabel": dates["label"],
                "actionYear": dates["year"],
                "posthumous": posthumous,
                "posthumousMarked": "posthumously" in text.lower(),
                "citation": citation,
                "enteredServiceAt": None,
                "birth": None,
                "birthYear": None,
                "accreditedTo": None,
                "homeState": find_state(citation[:400]),
                "issueDate": None,
                "generalOrder": order["number"],
                "sourceUrl": pdf_url,
                "sourceLabel": f"U.S. Army General Orders, {order['number']}",
                "extraSources": [detail_url],
                "campaignFile": None,
                "nameNotes": [],
                "continuesPerson": False,
            }
        )
        print(" added", parts["display"], conflict, dates["year"])
    cache.write_text(json.dumps(added, ensure_ascii=False, indent=2), encoding="utf-8")
    return added


if __name__ == "__main__":
    from parse_army import load_army_awards

    base = load_army_awards()
    extra = load_supplements(base)
    print("supplements", len(extra))
