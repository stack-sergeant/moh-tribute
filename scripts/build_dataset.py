"""Compile recipient profiles, battle hubs, a CSV, and dataset stats.

Run from the repository root:

    python3 scripts/build_dataset.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mohlib import slugify, squash
from parse_army import load_army_awards
from supplement_ago import load_supplements

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ERA_ORDER = [
    "Civil War",
    "Indian Wars",
    "Expeditions, 1871–1933",
    "World War I",
    "World War II",
    "Korean War",
    "Vietnam War",
    "Since 1975",
    "Peacetime and other actions",
]


def slim_award(award: dict) -> dict:
    return {
        "awardId": award["awardId"],
        "rank": award.get("rank") or None,
        "unit": award.get("unit") or None,
        "branch": award["branch"],
        "conflict": award["conflict"],
        "era": award["era"],
        "actionPlace": award.get("actionPlace"),
        "actionDate": award.get("actionDate"),
        "actionDateEnd": award.get("actionDateEnd"),
        "actionDateLabel": award.get("actionDateLabel"),
        "actionYear": award.get("actionYear"),
        "posthumous": bool(award.get("posthumous")),
        "citation": award["citation"],
        "issueDate": award.get("issueDate"),
        "generalOrder": award.get("generalOrder"),
        "sourceUrl": award["sourceUrl"],
        "sourceLabel": award["sourceLabel"],
        "extraSources": award.get("extraSources") or [],
        "nameNotes": award.get("nameNotes") or [],
        "battleId": None,
    }


def group_people(awards: list[dict]) -> list[dict]:
    people: list[dict] = []
    by_birth: dict[tuple, dict] = {}
    for award in awards:
        award_view = slim_award(award)
        if award.get("continuesPerson") and people:
            people[-1]["awards"].append(award_view)
            continue
        birth_key = (award["identity"], award.get("birthYear"))
        if award.get("birthYear") and birth_key in by_birth:
            by_birth[birth_key]["awards"].append(award_view)
            continue
        person = {
            "id": "",
            "name": award["name"],
            "nameSort": award["nameSort"],
            "last": award["last"],
            "first": award["first"],
            "homeState": award.get("homeState"),
            "birth": award.get("birth"),
            "birthYear": award.get("birthYear"),
            "awards": [award_view],
            "photo": None,
            "wikipedia": None,
            "wikidataId": None,
        }
        people.append(person)
        if award.get("birthYear"):
            by_birth[birth_key] = person
    seen: dict[str, int] = {}
    for person in people:
        base = slugify(person["name"])
        seen[base] = seen.get(base, 0) + 1
        if seen[base] == 1:
            person["id"] = base
        else:
            year = person["birthYear"] or person["awards"][0].get("actionYear") or seen[base]
            person["id"] = f"{base}-{year}"
    # Second pass in case the first duplicate took the plain slug.
    taken = Counter(person["id"] for person in people)
    for person in people:
        if taken[person["id"]] > 1:
            year = person["birthYear"] or person["awards"][0].get("actionYear") or "n"
            person["id"] = f"{slugify(person['name'])}-{year}-{person['awards'][0]['awardId'][-6:]}"
    return people


def place_key(place: str) -> str:
    text = place.lower().replace("'", "").replace("’", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_battles(people: list[dict]) -> list[dict]:
    hubs = json.loads((DATA / "curated-hubs.json").read_text(encoding="utf-8"))
    assigned: dict[str, str] = {}
    for hub in hubs:
        for person in people:
            for award in person["awards"]:
                if award["awardId"] in assigned:
                    continue
                if award["conflict"] != hub["conflict"]:
                    continue
                if hub.get("years") and award.get("actionYear") not in hub["years"]:
                    continue
                blob = f"{award.get('actionPlace') or ''} {award.get('citation') or ''}".lower()
                if any(keyword in blob for keyword in hub["keywords"]):
                    assigned[award["awardId"]] = hub["id"]
                    award["battleId"] = hub["id"]
    battles = []
    for hub in hubs:
        members = []
        for person in people:
            matched = [award for award in person["awards"] if award.get("battleId") == hub["id"]]
            if matched:
                members.append(person["id"])
        battles.append(
            {
                "id": hub["id"],
                "title": hub["title"],
                "conflict": hub["conflict"],
                "era": hub["era"],
                "dateLabel": hub["dateLabel"],
                "location": hub["location"],
                "summary": hub["summary"],
                "curated": True,
                "media": hub["media"],
                "recipientIds": members,
            }
        )
    groups: dict[tuple, list] = defaultdict(list)
    for person in people:
        for award in person["awards"]:
            if award.get("battleId"):
                continue
            if award.get("actionPlace"):
                key = ("place", award["conflict"], place_key(award["actionPlace"]))
            else:
                key = ("solo", award["awardId"])
            groups[key].append((person, award))
    for key, rows in groups.items():
        conflict = rows[0][1]["conflict"]
        era = rows[0][1]["era"]
        if key[0] == "place":
            # Prefer the longest recorded place string as the display name.
            place = max((row[1]["actionPlace"] for row in rows), key=len)
            title = place
            battle_id = slugify(f"{conflict}-{place}")[:80]
            years = sorted({row[1]["actionYear"] for row in rows if row[1].get("actionYear")})
            if len(years) == 1:
                date_label = str(years[0])
            elif years:
                date_label = f"{years[0]}–{years[-1]}"
            else:
                date_label = "Date not recorded in the citation entry"
            count = len(rows)
            word = "recipient" if count == 1 else "recipients"
            summary = (
                f"{count} {word} in the {conflict} have an official citation entry "
                f"placing the action at {place}. "
                "This page was grouped from those entries. Articles, footage, books, and films "
                "have not been curated for this action yet."
            )
        else:
            person, award = rows[0]
            place = None
            when = award.get("actionDateLabel") or (
                str(award["actionYear"]) if award.get("actionYear") else "an unrecorded date"
            )
            title = f"{person['name']}, {when}"
            battle_id = slugify(f"action-{person['id']}-{award['awardId']}")[:90]
            date_label = when
            summary = (
                f"The official citation for {person['name']} does not name a shared battle "
                f"that this archive has grouped with other recipients. "
                f"The recorded action is dated {when}, during the {conflict}."
            )
        # Avoid colliding with a curated id or another auto id.
        existing = {battle["id"] for battle in battles}
        base_id = battle_id
        n = 2
        while battle_id in existing:
            battle_id = f"{base_id}-{n}"
            n += 1
        recipient_ids = []
        for person, award in rows:
            award["battleId"] = battle_id
            if person["id"] not in recipient_ids:
                recipient_ids.append(person["id"])
        battles.append(
            {
                "id": battle_id,
                "title": title,
                "conflict": conflict,
                "era": era,
                "dateLabel": date_label,
                "location": place,
                "summary": summary,
                "curated": False,
                "media": [],
                "recipientIds": recipient_ids,
            }
        )
    return battles


def write_csv(people: list[dict]) -> None:
    path = DATA / "awards.csv"
    fields = [
        "person_id",
        "name",
        "award_id",
        "rank",
        "branch",
        "unit",
        "conflict",
        "era",
        "home_state",
        "posthumous",
        "action_date",
        "action_place",
        "battle_id",
        "source_url",
        "source_label",
        "citation",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for person in people:
            for award in person["awards"]:
                writer.writerow(
                    {
                        "person_id": person["id"],
                        "name": person["name"],
                        "award_id": award["awardId"],
                        "rank": award.get("rank") or "",
                        "branch": award["branch"],
                        "unit": award.get("unit") or "",
                        "conflict": award["conflict"],
                        "era": award["era"],
                        "home_state": person.get("homeState") or "",
                        "posthumous": "yes" if award["posthumous"] else "no",
                        "action_date": award.get("actionDate") or "",
                        "action_place": award.get("actionPlace") or "",
                        "battle_id": award.get("battleId") or "",
                        "source_url": award["sourceUrl"],
                        "source_label": award["sourceLabel"],
                        "citation": award["citation"],
                    }
                )


def write_stats(people: list[dict], battles: list[dict]) -> dict:
    awards = [award for person in people for award in person["awards"]]
    by_conflict = Counter(award["conflict"] for award in awards)
    by_era = Counter(award["era"] for award in awards)
    by_branch = Counter(award["branch"] for award in awards)
    photos = sum(1 for person in people if person.get("photo"))
    stats = {
        "people": len(people),
        "awards": len(awards),
        "doubleRecipientsInThisArchive": sum(1 for person in people if len(person["awards"]) > 1),
        "byConflict": dict(by_conflict.most_common()),
        "byEra": {era: by_era.get(era, 0) for era in ERA_ORDER},
        "byBranch": dict(by_branch.most_common()),
        "posthumousAwards": sum(1 for award in awards if award["posthumous"]),
        "awardsWithPlace": sum(1 for award in awards if award.get("actionPlace")),
        "peopleWithHomeState": sum(1 for person in people if person.get("homeState")),
        "peopleWithPhoto": photos,
        "photoPercent": round(100 * photos / len(people), 1) if people else 0,
        "battles": len(battles),
        "curatedBattles": [
            {"id": battle["id"], "title": battle["title"], "recipients": len(battle["recipientIds"])}
            for battle in battles
            if battle["curated"]
        ],
        "autoBattles": sum(1 for battle in battles if not battle["curated"]),
        "officialComparison": (
            "Public counts in 2025–2026 are usually given as more than 3,500 awards, "
            "about 3,526 people after the January 3, 2025 ceremony, with further awards in 2026. "
            "This archive counts one row per award in the U.S. Army citation index plus Army general orders "
            "that were not already in that index. Navy, Marine Corps, Air Force, and Coast Guard awards "
            "are included when the Army index carries them. Rescinded 1917 awards are not included."
        ),
    }
    (DATA / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def apply_photo_cache(people: list[dict]) -> None:
    cache = DATA / "photos.json"
    if not cache.exists():
        return
    photos = json.loads(cache.read_text(encoding="utf-8"))
    for person in people:
        extra = photos.get(person["id"])
        if not extra:
            continue
        person["photo"] = extra.get("photo")
        person["wikipedia"] = extra.get("wikipedia")
        person["wikidataId"] = extra.get("wikidataId")


def main() -> None:
    awards = load_army_awards()
    print(f"army index awards: {len(awards)}")
    try:
        extra = load_supplements(awards)
    except Exception as error:
        print("supplement step failed:", error)
        extra = []
        cached = DATA / "awards-ago.json"
        if cached.exists():
            extra = json.loads(cached.read_text(encoding="utf-8"))
    print(f"general-order supplements: {len(extra)}")
    awards.extend(extra)
    people = group_people(awards)
    apply_photo_cache(people)
    battles = build_battles(people)
    people.sort(key=lambda person: person["nameSort"].lower())
    (DATA / "recipients.json").write_text(
        json.dumps(people, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA / "battles.json").write_text(
        json.dumps(battles, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(people)
    stats = write_stats(people, battles)
    print(json.dumps({k: stats[k] for k in ("people", "awards", "photoPercent", "battles", "curatedBattles")}, indent=2))


if __name__ == "__main__":
    main()
