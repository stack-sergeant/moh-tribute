"""Find free public-domain portraits for recipients who do not have one.

Searches the National Archives Catalog, the Library of Congress Prints &
Photographs catalog, Wikimedia Commons, and Chronicling America. A portrait
is kept only when the name agrees and at least one of the award, the unit,
or the war-and-dates also agrees. Ambiguous names are skipped. Images that
exist only as undigitized photographs are listed for later approval and are
not downloaded. Nothing is generated, colorized, or restored.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "photo-hunt"
PHOTO_DIR = ROOT / "public" / "photos"
UA = "ValorRecordDataPipeline/1.0 (educational archive; info@praxistechllc.com)"
FETCH_LOCK = threading.Lock()

RANKS = {
    "gen", "general", "brig", "brigadier", "maj", "major", "col", "colonel",
    "lt", "lieut", "lieutenant", "capt", "captain", "sgt", "sergeant", "cpl",
    "corporal", "pvt", "private", "adm", "admiral", "cmdr", "commander",
    "ens", "ensign", "rear", "vice", "bvt", "brevet", "hon", "honorable",
    "dr", "doctor", "sir", "mr", "mrs", "miss",
}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
PORTRAIT_WORDS = {
    "half", "length", "portrait", "photograph", "photo", "head", "shoulders",
    "facing", "front", "right", "left", "bust", "seated", "standing", "view",
    "image", "print", "negative", "albumen", "carte", "visite", "cdv", "full",
    "three", "quarter", "profile", "outdoor", "studio", "copy", "reproduction",
}
GENERIC_UNITS = {
    "", "u.s. navy", "u.s. army", "u.s. marine corps", "u.s. marines",
    "u.s. volunteers", "u.s. army air forces", "u.s. air force",
    "u.s. coast guard", "indian scouts", "u.s. marine corps reserve",
}
WAR_WORDS = {
    "Civil War": ["civil war", "1861", "1862", "1863", "1864", "1865", "union army", "confederate"],
    "Indian Wars": ["indian war", "indian wars", "apache", "sioux", "nez perce", "modoc"],
    "Spanish–American War": ["spanish-american", "spanish american", "1898"],
    "Philippine–American War": ["philippine"],
    "Boxer Rebellion": ["boxer"],
    "World War I": ["world war i", "world war 1", "great war", "1918", "1917"],
    "World War II": ["world war ii", "world war 2", "1941", "1942", "1943", "1944", "1945"],
    "Korean War": ["korean war", "korea"],
    "Vietnam War": ["vietnam"],
    "War in Afghanistan": ["afghanistan"],
    "Iraq War": ["iraq"],
}
AI_WORDS = (
    "artificial intelligence", "ai-generated", "ai generated", "ai-restored",
    "ai restored", "stable diffusion", "midjourney", "neural", "digitally restored",
    "digitally colorized", "colorized", "colourised", "colorised",
)
ORDINALS = {
    "1st": "first", "2d": "second", "2nd": "second", "3d": "third", "3rd": "third",
    "4th": "fourth", "5th": "fifth", "6th": "sixth", "7th": "seventh",
    "8th": "eighth", "9th": "ninth", "10th": "tenth",
}


def cache_path(url: str) -> Path:
    digest = hashlib.sha1(url.encode()).hexdigest()
    return CACHE / digest[:2] / f"{digest}.json"


def fetch(url: str, accept: str = "application/json", timeout: int = 45) -> dict | list | None:
    path = cache_path(url)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.unlink()
    delay = 2
    last = None
    for _ in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                ctype = response.headers.get("content-type", "")
            if raw[:1] not in (b"{", b"["):
                return {"_error": "not-json", "ctype": ctype, "head": raw[:120].decode("utf-8", "replace")}
            data = json.loads(raw.decode("utf-8"))
            with FETCH_LOCK:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data), encoding="utf-8")
            return data
        except urllib.error.HTTPError as error:
            last = error
            if error.code not in (429, 500, 502, 503):
                return {"_error": f"http-{error.code}"}
            time.sleep(delay)
            delay *= 2
        except Exception as error:  # noqa: BLE001 - network failures are recorded and skipped
            last = error
            time.sleep(delay)
            delay *= 2
    return {"_error": str(last)}


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(as_text(part) for part in value.values())
    if isinstance(value, list):
        return " ".join(as_text(part) for part in value)
    return str(value)


def clean(text: str) -> str:
    text = text or ""
    text = text.replace("’", "'").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", clean(text).lower())


def person_parts(person: dict) -> tuple[str, str, str]:
    tokens = [re.sub(r"[^A-Za-z]", "", part) for part in person["name"].split()]
    tokens = [part for part in tokens if part and part.lower() not in SUFFIXES]
    if len(tokens) < 2:
        return person["first"].lower(), "", person["last"].lower()
    first = tokens[0].lower()
    last = tokens[-1].lower()
    middle = ""
    if len(tokens) >= 3:
        middle = tokens[1][0].lower()
    return first, middle, last


def distinctive_unit(unit: str | None) -> str | None:
    unit = clean(unit or "")
    if unit.lower() in GENERIC_UNITS:
        return None
    if "," in unit:
        unit = unit.split(",", 1)[1].strip()
    unit = re.sub(r"^company\s+[a-z0-9]+\s+", "", unit, flags=re.I)
    if len(unit) < 8 or unit.lower() in GENERIC_UNITS:
        return None
    return unit


def unit_in_text(unit: str | None, text: str) -> bool:
    phrase = distinctive_unit(unit)
    if not phrase:
        return False
    hay = " ".join(words(text))
    needed = words(phrase)
    # Drop a leading company letter that survived, and expand 8th/eighth.
    expanded = []
    for word in needed:
        expanded.append(word)
        if word in ORDINALS:
            expanded.append(ORDINALS[word])
    # The number (or its word) and the arm of service both have to be present.
    arms = [word for word in expanded if word in {
        "infantry", "cavalry", "artillery", "engineers", "cavalry", "battery",
        "marines", "navy", "volunteer", "volunteers", "scouts", "inf", "cav",
    }]
    numbers = [word for word in expanded if word[0].isdigit() or word in ORDINALS.values()]
    if numbers and not any(number in hay.split() for number in numbers):
        return False
    if arms and not any(arm in hay.split() for arm in arms):
        return False
    # State or ship words, ignoring very common fillers.
    fillers = {"u", "s", "us", "regiment", "company", "battalion", "corps", "light", "heavy", "volunteer", "volunteers"}
    rest = [word for word in needed if word not in fillers and word not in numbers and word not in arms and word not in ORDINALS]
    return all(word in hay.split() for word in rest)


def war_in_text(person: dict, text: str) -> bool:
    conflict = person["awards"][0].get("conflict") or ""
    hay = text.lower()
    for key, phrases in WAR_WORDS.items():
        if key == conflict and any(phrase in hay for phrase in phrases):
            return True
    era = (person["awards"][0].get("era") or "").lower()
    if "civil war" in era and "civil war" in hay:
        return True
    if "indian" in era and "indian" in hay:
        return True
    year = person["awards"][0].get("actionYear")
    if year and str(year) in hay:
        return True
    return False


def mentions_medal(text: str) -> bool:
    hay = text.lower()
    return "medal of honor" in hay or "congressional medal" in hay


def looks_generated(text: str) -> bool:
    hay = text.lower()
    return any(word in hay for word in AI_WORDS)


def looks_like_group(title: str) -> bool:
    hay = title.lower()
    return any(phrase in hay for phrase in (
        "left to right", "l to r", "group of", "group portrait", "group photo",
        "and others", "medal of honor men", "class of", "staff of", "delegation",
        "crowd", "attendees", "gathered", "remembering", "in memory", "memorial",
        "grave", "gravesite", "cemetery", "headstone", "wreath", "tomb of", "burial",
        "descendants", "family of", "family plot", "plaque", "citation", "signature",
        "honors memory", "honors the memory", "list of", "letter from",
    ))


def title_names_person(title: str, person: dict) -> tuple[bool, str]:
    first, middle, last = person_parts(person)
    tokens = words(title)
    if first not in tokens or last not in tokens:
        return False, "name-not-in-title"
    # First name (or initial) must sit just before the surname, with at most a middle initial between.
    last_at = [index for index, token in enumerate(tokens) if token == last]
    good = False
    for index in last_at:
        window = tokens[max(0, index - 3):index]
        if first in window or first[:1] in window:
            between = tokens[index - 1] if index else ""
            if middle and between and between != middle and between != first and len(between) > 1 and between not in RANKS:
                # A different middle name sits against this surname.
                continue
            following = tokens[index + 1] if index + 1 < len(tokens) else ""
            if (
                following
                and following not in SUFFIXES | RANKS | PORTRAIT_WORDS | {"usa", "usn", "usmc", "army", "navy"}
                and len(following) > 2
                and not following[0].isdigit()
            ):
                # "James Adams Ekin": Adams is not the surname.
                if following not in words(distinctive_unit(person["awards"][0].get("unit")) or ""):
                    continue
            good = True
            break
    if not good:
        return False, "name-not-the-subject"
    return True, "ok"


def confirmation(person: dict, text: str, title: str) -> tuple[int, str]:
    if looks_generated(text) or looks_generated(title):
        return 0, "generated-or-restored"
    if looks_like_group(title):
        return 0, "group"
    named, why = title_names_person(title, person)
    if not named:
        return 0, why
    first, middle, _last = person_parts(person)
    title_tokens = words(title)
    middle_ok = bool(middle) and middle in title_tokens and first in title_tokens
    if mentions_medal(text):
        return 5, "medal"
    if unit_in_text(person["awards"][0].get("unit"), text):
        return 4, "unit"
    if middle_ok and war_in_text(person, text):
        return 3, "name-and-war"
    return 0, "ambiguous"


def roster_unique(person: dict, people_by_name: dict) -> bool:
    first, _middle, last = person_parts(person)
    return len(people_by_name.get((last, first), [])) == 1


def acceptable(person: dict, title: str, text: str, people_by_name: dict) -> tuple[bool, str, int]:
    score, reason = confirmation(person, f"{title} {text}", title)
    if score < 3:
        return False, reason, score
    first, middle, last = person_parts(person)
    siblings = people_by_name.get((last, first), [])
    if len(siblings) > 1:
        # Another recipient shares the name. Keep this one only when the middle initial is in the title.
        if not middle or middle not in words(title):
            return False, "shared-name", score
    if reason == "name-and-war" and not roster_unique(person, people_by_name):
        return False, "shared-name", score
    return True, reason, score


def nara_search(query: str, online: str | None = None) -> list[dict]:
    params = {
        "q": query,
        "typeOfMaterials": "Photographs and other Graphic Materials",
        "limit": 15,
    }
    if online:
        params["availableOnline"] = online
    url = "https://catalog.archives.gov/proxy/v3/records/search?" + urllib.parse.urlencode(params)
    data = fetch(url)
    if not isinstance(data, dict) or data.get("_error"):
        return []
    hits = data.get("body", {}).get("hits", {}).get("hits") or []
    records = []
    for hit in hits:
        record = (hit.get("_source") or {}).get("record") or {}
        if record:
            records.append(record)
    return records


def nara_text(record: dict) -> tuple[str, str]:
    ancestors = " ".join(ancestor.get("title") or "" for ancestor in record.get("ancestors") or [])
    scope = record.get("scopeAndContentNote") or ""
    if isinstance(scope, list):
        scope = " ".join(str(part) for part in scope)
    title = clean(record.get("title") or "")
    return title, clean(f"{title} {scope} {ancestors}")


def nara_image(record: dict) -> str | None:
    objects = record.get("digitalObjects") or []
    images = []
    for obj in objects:
        url = obj.get("objectUrl") or ""
        kind = (obj.get("objectType") or "").lower()
        if not url:
            continue
        if "image" in kind or re.search(r"\.(jpe?g|gif|tif|png|webp)$", url, re.I):
            images.append((obj.get("objectFileSize") or 0, url))
    if not images:
        return None
    images.sort(reverse=True)
    # Prefer a jpeg over a gif when both exist and the jpeg is not tiny.
    jpegs = [url for _size, url in images if re.search(r"\.jpe?g$", url, re.I)]
    return jpegs[0] if jpegs else images[0][1]


def loc_search(query: str) -> list[dict]:
    url = "https://www.loc.gov/pictures/search/?" + urllib.parse.urlencode({"q": query, "fo": "json", "c": 10})
    data = fetch(url)
    if not isinstance(data, dict) or data.get("_error"):
        return []
    return data.get("results") or []


def loc_item(pk: str) -> dict:
    url = f"https://www.loc.gov/pictures/item/{pk}/?fo=json"
    data = fetch(url)
    return data if isinstance(data, dict) else {}


def loc_rights_ok(item: dict) -> tuple[bool, str]:
    rights = clean((item.get("item") or {}).get("rights_information") or "")
    hay = rights.lower()
    if item.get("unrestricted") is True or "no known restrictions" in hay or "public domain" in hay:
        if "restricted" in hay and "no known restrictions" not in hay:
            return False, rights
        return True, rights or "No known restrictions on publication."
    return False, rights or "rights not stated"


def commons_search(query: str) -> list[dict]:
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "list": "search",
        "srnamespace": "6",
        "srlimit": "8",
        "srsearch": query,
    })
    data = fetch(url)
    if not isinstance(data, dict) or data.get("_error"):
        return []
    return (data.get("query") or {}).get("search") or []


def commons_info(titles: list[str]) -> dict:
    if not titles:
        return {}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": "900",
        "titles": "|".join(titles),
    })
    data = fetch(url)
    found = {}
    if not isinstance(data, dict):
        return found
    for page in (data.get("query") or {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [None])[0]
        if info:
            found[page.get("title") or ""] = info
    return found


def commons_license(info: dict) -> tuple[bool, str, str]:
    extra = info.get("extmetadata") or {}

    def value(key: str) -> str:
        raw = (extra.get(key) or {}).get("value") or ""
        return re.sub(r"<[^>]+>", " ", raw)

    blob = f"{value('LicenseShortName')} {value('UsageTerms')}".lower().replace("-", " ").replace("–", " ")
    if any(bad in blob for bad in ("noncommercial", "non commercial", "fair use", "all rights reserved", "no derivatives", " noderiv")):
        return False, value("LicenseShortName"), value("LicenseUrl")
    if not any(good in blob for good in ("public domain", "cc0", "cc by", "creative commons attribution")):
        return False, value("LicenseShortName"), value("LicenseUrl")
    if "sa" in blob and "cc by sa" not in blob and "attribution share" not in blob and "share alike" not in blob:
        pass
    # CC BY-ND already rejected. CC BY and CC BY-SA remain.
    if "nd" in re.findall(r"\bnd\b", blob):
        return False, value("LicenseShortName"), value("LicenseUrl")
    return True, value("LicenseShortName") or value("UsageTerms"), value("LicenseUrl")


def download_image(url: str, dest: Path) -> tuple[bool, int, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = dest.with_suffix(".src")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read(12_000_000)
    except Exception:
        return False, 0, 0
    if len(data) < 20_000:
        return False, 0, 0
    raw.write_bytes(data)
    made = subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
            "-vf", "scale='min(800,iw)':-2", "-q:v", "6", str(dest),
        ],
        check=False,
    )
    raw.unlink(missing_ok=True)
    if made.returncode != 0 or not dest.exists() or dest.stat().st_size < 8_000:
        dest.unlink(missing_ok=True)
        return False, 0, 0
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(dest)],
        capture_output=True, text=True, check=False,
    )
    parts = (probe.stdout or "").strip().split(",")
    if len(parts) != 2 or not parts[0].isdigit():
        dest.unlink(missing_ok=True)
        return False, 0, 0
    width, height = int(parts[0]), int(parts[1])
    if width < 280 or height < 280:
        dest.unlink(missing_ok=True)
        return False, 0, 0
    return True, width, height


def fee_in_text(text: str) -> str:
    match = re.search(r"\$\s?\d+(?:\.\d{2})?", text or "")
    return match.group(0) if match else ""


def consider(person, title, text, people_by_name, source, item_url, image_url, rights, creator) -> dict:
    ok, reason, score = acceptable(person, title, text, people_by_name)
    return {
        "ok": ok,
        "reason": reason,
        "score": score,
        "source": source,
        "title": title[:240],
        "itemUrl": item_url,
        "imageUrl": image_url,
        "rights": rights[:240],
        "creator": clean(creator)[:240],
        "fee": fee_in_text(text),
    }


def hunt_person(person: dict, people_by_name: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Return accepted candidates, ambiguous skips, and paid-only candidates."""
    first, middle, last = person_parts(person)
    display = person["name"]
    phrase = f'"{display}"'
    unit = distinctive_unit(person["awards"][0].get("unit"))
    query = f"{phrase} \"{unit}\"" if unit else phrase
    accepted, skipped, paid = [], [], []

    for record in nara_search(query):
        title, text = nara_text(record)
        use = ((record.get("useRestriction") or {}).get("status") or "")
        image = nara_image(record)
        naid = record.get("naId")
        item_url = f"https://catalog.archives.gov/id/{naid}"
        if use.lower() != "unrestricted":
            named, _why = title_names_person(title, person)
            if named:
                skipped.append({"id": person["id"], "name": display, "source": "NARA", "reason": f"use-{use or 'unstated'}", "title": title[:180], "url": item_url})
            continue
        decision = consider(person, title, text, people_by_name, "NARA", item_url, image, "Public domain. Unrestricted U.S. National Archives record.", "")
        if not decision["ok"]:
            if decision["reason"] in {"ambiguous", "shared-name", "group", "generated-or-restored"}:
                skipped.append({"id": person["id"], "name": display, "source": "NARA", "reason": decision["reason"], "title": title[:180], "url": item_url})
            continue
        if not image:
            paid.append({"recipient": display, "source": "NARA", "item_url": item_url, "fee": decision["fee"], "note": "Photograph record has no digital image online."})
            continue
        decision["id"] = person["id"]
        accepted.append(decision)

    for result in loc_search(query):
        pk = str(result.get("pk") or "")
        rough_title = clean(result.get("title") or "")
        if not pk or not title_names_person(rough_title, person)[0]:
            continue
        item = loc_item(pk)
        inner = item.get("item") or {}
        title = clean(inner.get("title") or result.get("title") or "")
        subjects = as_text(inner.get("subjects") or result.get("subjects") or [])
        summary = as_text(inner.get("summary") or "")
        text = clean(f"{title} {subjects} {summary} {as_text(inner.get('created_published'))}")
        rights_ok, rights = loc_rights_ok(item)
        item_url = (result.get("links") or {}).get("item") or f"https://www.loc.gov/pictures/item/{pk}/"
        medium = inner.get("service_medium")
        medium_url = medium[0] if isinstance(medium, list) and medium else None
        image = ((result.get("image") or {}).get("full")) or medium_url
        creator = inner.get("creators") or result.get("creator") or ""
        if isinstance(creator, list):
            creator = "; ".join(str(part.get("title") if isinstance(part, dict) else part) for part in creator)
        if not rights_ok:
            named, _why = title_names_person(title, person)
            if named:
                skipped.append({"id": person["id"], "name": display, "source": "Library of Congress", "reason": "rights", "title": title[:180], "url": item_url})
            continue
        decision = consider(person, title, text, people_by_name, "Library of Congress", item_url, image, rights, str(creator))
        if not decision["ok"]:
            if decision["reason"] in {"ambiguous", "shared-name", "group", "generated-or-restored"}:
                skipped.append({"id": person["id"], "name": display, "source": "Library of Congress", "reason": decision["reason"], "title": title[:180], "url": item_url})
            continue
        if not image:
            paid.append({"recipient": display, "source": "Library of Congress", "item_url": item_url, "fee": decision["fee"], "note": "Prints & Photographs record has no digital image online."})
            continue
        decision["id"] = person["id"]
        accepted.append(decision)

    # Commons: only files whose title or description names the person and the award.
    commons_query = f'{display} "Medal of Honor"'
    hits = commons_search(commons_query)
    titles = [hit.get("title") for hit in hits if hit.get("title")]
    infos = commons_info(titles) if titles else {}
    for title in titles:
        info = infos.get(title) or {}
        if not info or str(info.get("mime", "")).endswith("svg"):
            continue
        licensed, license_name, license_url = commons_license(info)
        extra = info.get("extmetadata") or {}
        desc = re.sub(r"<[^>]+>", " ", (extra.get("ImageDescription") or {}).get("value") or "")
        artist = re.sub(r"<[^>]+>", " ", (extra.get("Artist") or {}).get("value") or "")
        file_title = title.replace("File:", "").replace("_", " ")
        text = clean(f"{file_title} {desc}")
        page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        if not licensed:
            named, _why = title_names_person(file_title, person)
            if named:
                skipped.append({"id": person["id"], "name": display, "source": "Wikimedia Commons", "reason": "license", "title": file_title[:180], "url": page})
            continue
        decision = consider(person, file_title, text, people_by_name, "Wikimedia Commons", page, info.get("thumburl") or info.get("url"), license_name, artist)
        decision["licenseUrl"] = license_url
        if not decision["ok"]:
            if decision["reason"] in {"ambiguous", "shared-name", "group", "generated-or-restored"}:
                skipped.append({"id": person["id"], "name": display, "source": "Wikimedia Commons", "reason": decision["reason"], "title": file_title[:180], "url": page})
            continue
        decision["id"] = person["id"]
        accepted.append(decision)
    return accepted, skipped, paid


def harvest_loc_medal(people: list[dict], people_by_name: dict) -> tuple[list[dict], list[dict], list[dict]]:
    accepted, skipped, paid = [], [], []
    # The Prints & Photographs phrase search is a few hundred items, not one per person.
    first = loc_search('"medal of honor"')
    # loc_search only returns the first page. Walk pages from the payload via a direct loop.
    page = 1
    seen = 0
    while page <= 12:
        url = "https://www.loc.gov/pictures/search/?" + urllib.parse.urlencode({
            "q": '"medal of honor"', "fo": "json", "c": 50, "sp": page,
        })
        data = fetch(url)
        results = (data or {}).get("results") or [] if isinstance(data, dict) else []
        if not results:
            break
        seen += len(results)
        for result in results:
            pk = str(result.get("pk") or "")
            title = clean(result.get("title") or "")
            if not pk or looks_like_group(title) or looks_generated(title):
                continue
            for person in people:
                if person["last"].lower() not in title.lower():
                    continue
                item = loc_item(pk)
                inner = item.get("item") or {}
                full_title = clean(inner.get("title") or title)
                subjects = as_text(inner.get("subjects") or result.get("subjects") or [])
                text = clean(f"{full_title} {subjects}")
                rights_ok, rights = loc_rights_ok(item)
                item_url = (result.get("links") or {}).get("item") or f"https://www.loc.gov/pictures/item/{pk}/"
                image = ((result.get("image") or {}).get("full"))
                if not rights_ok:
                    continue
                decision = consider(person, full_title, text, people_by_name, "Library of Congress", item_url, image, rights, str(result.get("creator") or ""))
                if decision["ok"] and image:
                    decision["id"] = person["id"]
                    accepted.append(decision)
                elif decision["reason"] in {"ambiguous", "shared-name", "group"}:
                    skipped.append({"id": person["id"], "name": person["name"], "source": "Library of Congress", "reason": decision["reason"], "title": full_title[:180], "url": item_url})
        page += 1
        if seen and not (data.get("pages") or {}).get("next") and page > 1:
            # Some responses use pages.total. Stop when a short page comes back.
            if len(results) < 50:
                break
    return accepted, skipped, paid


def chronicling_america() -> dict:
    url = "https://www.loc.gov/collections/chronicling-america/?" + urllib.parse.urlencode({
        "q": '"medal of honor" portrait',
        "end_date": "1930-12-31",
        "fo": "json",
        "c": 100,
        "at": "results,pagination",
    })
    data = fetch(url)
    results = (data or {}).get("results") or [] if isinstance(data, dict) else []
    formats = {}
    for result in results:
        for fmt in result.get("original_format") or ["unknown"]:
            formats[fmt] = formats.get(fmt, 0) + 1
    total = ((data or {}).get("pagination") or {}).get("of") if isinstance(data, dict) else None
    return {
        "query": '"medal of honor" portrait',
        "reportedTotal": total,
        "sampled": len(results),
        "formats": formats,
        "usedAsPortraits": 0,
        "note": "Results are full newspaper pages. A page is not a confirmed portrait of one recipient, so none were used as likenesses.",
    }


def probe_other_sources() -> dict:
    probes = {
        "NHHC": "https://www.history.navy.mil/our-collections/photography.html",
        "USMC History Division": "https://www.usmcu.edu/Research/Marine-Corps-History-Division/",
        "USAHEC": "https://arena.usahec.org/",
        "DVIDS": "https://api.dvidshub.net/search?q=medal%20of%20honor&type=image",
    }
    report = {}
    for name, url in probes.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html"})
            with urllib.request.urlopen(req, timeout=25) as response:
                report[name] = {"url": url, "status": response.status, "type": response.headers.get("content-type", "")}
        except Exception as error:  # noqa: BLE001
            report[name] = {"url": url, "error": str(error)}
    return report


def best_by_person(candidates: list[dict]) -> dict[str, dict]:
    chosen = {}
    for candidate in candidates:
        current = chosen.get(candidate["id"])
        if current is None or candidate["score"] > current["score"]:
            chosen[candidate["id"]] = candidate
    return chosen


def apply_candidate(photos: dict, person_id: str, candidate: dict, width: int, height: int) -> None:
    record = photos.get(person_id) or {"photo": None, "wikipedia": None, "wikidataId": None}
    credit = candidate["creator"]
    if credit:
        credit = f"{credit}. {candidate['source']}."
    else:
        credit = f"{candidate['source']}."
    record["photo"] = {
        "url": f"/photos/{person_id}.jpg",
        "pageUrl": candidate["itemUrl"],
        "license": candidate["rights"],
        "licenseUrl": candidate.get("licenseUrl") or None,
        "credit": clean(credit)[:400],
        "width": width,
        "height": height,
        "source": candidate["source"],
    }
    photos[person_id] = record


def self_test() -> None:
    person = {
        "id": "joshua-l-chamberlain",
        "name": "Joshua L. Chamberlain",
        "first": "Joshua",
        "last": "Chamberlain",
        "awards": [{"unit": "20th Maine Infantry", "conflict": "Civil War", "era": "Civil War", "actionYear": 1863}],
    }
    adams = {
        "id": "james-f-adams",
        "name": "James F. Adams",
        "first": "James",
        "last": "Adams",
        "awards": [{"unit": "Company D, 1st West Virginia Cavalry", "conflict": "Civil War", "era": "Civil War", "actionYear": 1864}],
    }
    allen = {
        "id": "james-allen",
        "name": "James Allen",
        "first": "James",
        "last": "Allen",
        "awards": [{"unit": "Company F, 16th New York Infantry", "conflict": "Civil War", "era": "Civil War", "actionYear": 1862}],
    }
    people_by_name = {
        ("chamberlain", "joshua"): [person],
        ("adams", "james"): [adams],
        ("allen", "james"): [allen, {**allen, "id": "other"}],
    }
    cases = [
        (person, "Gen. Joshua L. Chamberlain", "19th Century Mathew Brady and other Civil War Photographs", True),
        (person, "Joshua L. Chamberlain, half-length portrait, facing right", "Civil War photograph", True),
        (person, "Edwin H. Stoughton", "mentions Joshua Chamberlain in a letter", False),
        (adams, "Brigadier General James Adams Ekin, 12th Pennsylvania Infantry", "Civil War", False),
        (adams, "Private James F. Adams, 1st West Virginia Cavalry", "Civil War photograph", True),
        (allen, "James Allen, half-length portrait", "Civil War photograph", False),
        (person, "Joshua L. Chamberlain", "AI-restored Civil War portrait, Medal of Honor", False),
        (person, "Medal of honor men", "Joshua L. Chamberlain is in the group, Civil War", False),
        (person, "Remembering Medal of Honor recipient Joshua L. Chamberlain", "Civil War", False),
    ]
    failed = 0
    for subject, title, text, expect in cases:
        ok, reason, score = acceptable(subject, title, text, people_by_name)
        print(("OK " if ok == expect else "FAIL"), ok, reason, score, title[:60])
        failed += ok != expect
    if failed:
        raise SystemExit(f"{failed} matcher checks failed")
    print("matcher checks passed")


def main() -> None:
    if "--self-test" in sys.argv:
        self_test()
        return
    people = json.loads((ROOT / "data" / "recipients.json").read_text(encoding="utf-8"))
    photos = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))
    people_by_name: dict[tuple[str, str], list] = {}
    for person in people:
        first, _middle, last = person_parts(person)
        people_by_name.setdefault((last, first), []).append(person)
    missing = [person for person in people if not person.get("photo")]
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
        missing = missing[:limit]
    print(f"searching {len(missing)} recipients without a photo", flush=True)

    accepted: list[dict] = []
    skipped: list[dict] = []
    paid: list[dict] = []
    if "--skip-harvest" not in sys.argv and limit is None:
        print("harvesting Library of Congress medal-of-honor photographs", flush=True)
        extra_a, extra_s, extra_p = harvest_loc_medal(missing, people_by_name)
        accepted.extend(extra_a)
        skipped.extend(extra_s)
        paid.extend(extra_p)
        print(f"  loc harvest accepted {len(extra_a)}", flush=True)

    def work(person: dict):
        return person["id"], hunt_person(person, people_by_name)

    done = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(work, person) for person in missing]
        for future in as_completed(futures):
            person_id, (got, skip, pay) = future.result()
            accepted.extend(got)
            skipped.extend(skip)
            paid.extend(pay)
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(missing)} searched, candidates {len(accepted)}", flush=True)

    chosen = best_by_person(accepted)
    # Do not replace a portrait the earlier pipeline already verified.
    already = {person["id"] for person in people if person.get("photo")}
    saved = 0
    by_source = {}
    too_small = []
    for person_id, candidate in chosen.items():
        if person_id in already:
            continue
        dest = PHOTO_DIR / f"{person_id}.jpg"
        ok, width, height = download_image(candidate["imageUrl"], dest)
        if not ok:
            too_small.append({
                "recipient": next(person["name"] for person in people if person["id"] == person_id),
                "source": candidate["source"],
                "item_url": candidate["itemUrl"],
                "fee": candidate.get("fee") or "",
                "note": "A matching record was found, but the online file was too small or would not decode. A reproduction may still be a paid scan.",
            })
            continue
        apply_candidate(photos, person_id, candidate, width, height)
        by_source[candidate["source"]] = by_source.get(candidate["source"], 0) + 1
        saved += 1
        if saved % 10 == 0:
            (ROOT / "data" / "photos.json").write_text(json.dumps(photos, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  saved {saved}", flush=True)
    (ROOT / "data" / "photos.json").write_text(json.dumps(photos, ensure_ascii=False, indent=2), encoding="utf-8")

    paid.extend(too_small)
    # One row per item URL.
    seen_urls = set()
    paid_rows = []
    for row in paid:
        if row["item_url"] in seen_urls:
            continue
        seen_urls.add(row["item_url"])
        paid_rows.append(row)
    with (ROOT / "data" / "paid-photo-candidates.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["recipient", "source", "item_url", "fee", "note"])
        writer.writeheader()
        writer.writerows(paid_rows)

    skip_counts = {}
    for row in skipped:
        skip_counts[row["reason"]] = skip_counts.get(row["reason"], 0) + 1
    chronicling = chronicling_america()
    probes = probe_other_sources()
    report = {
        "searched": len(missing),
        "newPhotos": saved,
        "bySource": by_source,
        "paidCandidates": len(paid_rows),
        "ambiguousSkipped": len(skipped),
        "skipReasons": skip_counts,
        "skipExamples": skipped[:40],
        "chroniclingAmerica": chronicling,
        "otherSources": probes,
    }
    (ROOT / "data" / "photo-hunt-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("newPhotos", "bySource", "paidCandidates", "ambiguousSkipped", "skipReasons")}, indent=2))


if __name__ == "__main__":
    main()
