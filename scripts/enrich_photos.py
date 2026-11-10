"""Attach Wikimedia photos only when the license and the name match.

Public-domain U.S. government works and Creative Commons images are kept.
Fair-use and non-commercial files are not. Nothing is generated.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mohlib import slugify

ROOT = Path(__file__).resolve().parents[1]
UA = "ValorRecordDataPipeline/1.0 (educational archive; info@praxistechllc.com)"
LETTERS = "abcdefghijklmnopqrstuvwxyz"


def post(url: str, payload: dict, accept: str) -> dict:
    data = urllib.parse.urlencode(payload).encode()
    delay = 5
    last_error = None
    for _ in range(6):
        req = urllib.request.Request(
            url,
            data=data,
            headers={"User-Agent": UA, "Accept": accept},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in (429, 500, 503):
                raise
            print(" retry", error.code, "sleep", delay, flush=True)
            time.sleep(delay)
            delay *= 2
    raise last_error


def fetch_wikidata() -> list[dict]:
    cache_dir = ROOT / "data" / "raw" / "wikidata"
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for letter in LETTERS:
        cache = cache_dir / f"{letter}.json"
        if cache.exists():
            rows.extend(json.loads(cache.read_text(encoding="utf-8")))
            continue
        query = f"""
        SELECT ?person ?personLabel ?birth ?image ?article WHERE {{
          ?person wdt:P166 wd:Q203535 .
          ?person rdfs:label ?personLabel .
          FILTER(LANG(?personLabel) = "en")
          FILTER(STRSTARTS(LCASE(?personLabel), "{letter}"))
          OPTIONAL {{ ?person wdt:P569 ?birth. }}
          OPTIONAL {{ ?person wdt:P18 ?image. }}
          OPTIONAL {{
            ?article schema:about ?person .
            ?article schema:isPartOf <https://en.wikipedia.org/> .
          }}
        }}
        """
        print("wikidata", letter, flush=True)
        result = post(
            "https://query.wikidata.org/sparql",
            {"query": query},
            "application/sparql-results+json",
        )
        letter_rows = []
        for binding in result["results"]["bindings"]:
            letter_rows.append(
                {
                    "id": binding["person"]["value"].rsplit("/", 1)[-1],
                    "label": binding["personLabel"]["value"],
                    "birth": binding.get("birth", {}).get("value", "")[:10],
                    "death": binding.get("death", {}).get("value", "")[:10],
                    "image": binding.get("image", {}).get("value"),
                    "article": binding.get("article", {}).get("value"),
                }
            )
        cache.write_text(json.dumps(letter_rows), encoding="utf-8")
        rows.extend(letter_rows)
        time.sleep(3)
    return rows


def split_label(label: str) -> tuple[str, str, str]:
    label = re.sub(r"\([^)]*\)", " ", label)
    parts = [part for part in re.split(r"\s+", label.strip()) if part]
    if len(parts) < 2:
        return "", "", ""
    last = parts[-1].strip(",")
    first = parts[0].strip(",")
    middle = parts[1] if len(parts) > 2 else ""
    return slugify(last), slugify(first), (middle[:1].lower() if middle else "")


def license_ok(meta: dict) -> tuple[bool, str, str]:
    def value(key: str) -> str:
        raw = (meta.get(key) or {}).get("value") or ""
        return re.sub(r"<[^>]+>", " ", raw)

    name = value("LicenseShortName")
    terms = value("UsageTerms")
    blob = f"{name} {terms}".lower()
    if any(bad in blob for bad in ("noncommercial", "non-commercial", "fair use", "all rights reserved")):
        return False, name, terms
    if not any(good in blob for good in ("public domain", "cc0", "cc by", "creative commons", "no restrictions", "pd-")):
        return False, name, terms
    return True, name or terms, value("LicenseUrl")


def commons_metadata(filenames: list[str]) -> dict:
    found = {}
    for start in range(0, len(filenames), 40):
        batch = filenames[start : start + 40]
        titles = "|".join("File:" + name.replace(" ", "_") for name in batch)
        url = "https://commons.wikimedia.org/w/api.php"
        result = post(
            url,
            {
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime|size",
                "iiurlwidth": "800",
                "titles": titles,
            },
            "application/json",
        )
        for page in result.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [None])[0]
            if not info:
                continue
            title = page.get("title", "").replace("File:", "")
            found[title] = info
            found[title.replace("_", " ")] = info
            found[urllib.parse.unquote(title)] = info
        time.sleep(0.3)
    return found


def main() -> None:
    people = json.loads((ROOT / "data" / "recipients.json").read_text(encoding="utf-8"))
    rows = fetch_wikidata()
    print("wikidata rows", len(rows), flush=True)
    by_name: dict[tuple, list] = {}
    for row in rows:
        last, first, middle = split_label(row["label"])
        if not last or not first:
            continue
        by_name.setdefault((last, first), []).append((middle, row))
    chosen = []
    for person in people:
        last = slugify(person["last"])
        first = slugify(person["first"])
        middle = ""
        # Middle initial is not stored separately; recover it from the display name.
        tokens = person["name"].split()
        if len(tokens) >= 3 and re.fullmatch(r"[A-Z]\.?", tokens[1]):
            middle = tokens[1][0].lower()
        candidates = []
        for cand_middle, row in by_name.get((last, first), []):
            if middle and cand_middle and middle != cand_middle:
                continue
            birth = person.get("birthYear")
            if birth and row["birth"][:4].isdigit() and abs(int(row["birth"][:4]) - birth) > 1:
                continue
            candidates.append(row)
        # One Wikidata item may repeat because of optional fields. Collapse by id.
        unique = {}
        for row in candidates:
            unique.setdefault(row["id"], row)
            if row.get("image") and not unique[row["id"]].get("image"):
                unique[row["id"]]["image"] = row["image"]
            if row.get("article") and not unique[row["id"]].get("article"):
                unique[row["id"]]["article"] = row["article"]
        if len(unique) != 1:
            continue
        row = next(iter(unique.values()))
        chosen.append((person["id"], person["last"], row))
    print("name matches", len(chosen), flush=True)
    filenames = []
    for _, _, row in chosen:
        if row.get("image"):
            name = urllib.parse.unquote(row["image"].rsplit("/", 1)[-1])
            row["filename"] = name
            filenames.append(name)
    meta = commons_metadata(filenames)
    photos = {}
    for person_id, last_name, row in chosen:
        record = {"photo": None, "wikipedia": row.get("article"), "wikidataId": row["id"]}
        info = meta.get(row.get("filename", ""))
        if info and not str(info.get("mime", "")).endswith("svg"):
            ok, license_name, license_url = license_ok(info.get("extmetadata") or {})
            filename = row.get("filename", "")
            lowered = filename.lower().replace("_", " ")
            if ok and "medal of honor" in lowered and last_name.lower() not in lowered:
                ok = False
            if ok:
                credit = ""
                extra = info.get("extmetadata") or {}
                for key in ("Artist", "Credit", "Attribution"):
                    raw = (extra.get(key) or {}).get("value") or ""
                    credit = re.sub(r"<[^>]+>", " ", raw)
                    credit = re.sub(r"\s+", " ", credit).strip()
                    if credit:
                        break
                record["photo"] = {
                    "url": info.get("thumburl") or info.get("url"),
                    "pageUrl": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(filename.replace(" ", "_")),
                    "license": license_name,
                    "licenseUrl": license_url or None,
                    "credit": credit[:400] or "Wikimedia Commons",
                    "width": info.get("thumbwidth"),
                    "height": info.get("thumbheight"),
                }
        photos[person_id] = record
    (ROOT / "data" / "photos.json").write_text(json.dumps(photos, ensure_ascii=False, indent=2), encoding="utf-8")
    with_photo = sum(1 for record in photos.values() if record.get("photo"))
    print("photos saved", with_photo, "of", len(photos), flush=True)


if __name__ == "__main__":
    main()
