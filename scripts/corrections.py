"""Corrections checked against CMOHS, the Army citation index, and NHHC.

The Army index snapshot mis-marks a few surviving recipients as posthumous,
and a handful of citation entries are truncated or mistyped. These overrides
keep a rebuild from putting that text back.
"""

from __future__ import annotations

import re

# CMOHS recipient page, quoted in full. The Army index prints a shorter,
# mistyped paragraph (15-19 November, "Bougaktroff", "Sergeant River's").
RIVERS_CITATION = (
    "For conspicuous gallantry and intrepidity at the risk of his life above and beyond "
    "the call of duty: Staff Sergeant Rivers distinguished himself by extraordinary heroism "
    "in action during 16-19 November 1944, while serving with Company A, 761st Tank Battalion. "
    "On 16 November 1944, while advancing toward the town of Guebling, France, Staff Sergeant "
    "Rivers' tank hit a mine at a railroad crossing. Although severely wounded, his leg slashed "
    "to the bone, Staff Sergeant Rivers declined an injection of morphine, refused to be evacuated, "
    "took command of another tank, and advanced with his company into Guebling the next day. "
    "Repeatedly refusing evacuation, Staff Sergeant Rivers continued to direct his tank's fire at "
    "enemy positions beyond the town through the morning of 19 November 1944. At dawn that day, "
    "Company A's tanks advanced toward Bourgaltoff, their next objective, but were stopped by "
    'enemy fire. Captain David J. Williams, the Company Commander, ordered his tanks to withdraw '
    "and take cover. Staff Sergeant Rivers, however, radioed that he had spotted the German "
    'antitank positions: "I see \'em. We\'ll Fight\'em!" Staff Sergeant Rivers, joined by another '
    "Company A tank, opened fire on enemy tanks, covering Company A as they withdrew. While doing "
    "so, Staff Sergeant Rivers' tank was hit, killing him and wounding the rest of the crew. "
    "Staff Sergeant Rivers' fighting spirit and daring leadership were an inspiration to his unit "
    "and exemplify the highest traditions of military service."
)

# CMOHS "Awarded Posthumously: No". The Army index puts an asterisk on the name.
NOT_POSTHUMOUS = {
    "bruce p. crandall",
    "dwight w. birdwell",
    "gary m. rose",
}

# Display-name overrides applied after the index is parsed.
FIELD_OVERRIDES = {
    "bruce p. crandall": {
        "posthumous": False,
        "actionPlace": "Landing Zone X-Ray, Ia Drang Valley, Vietnam",
        "unit": "Company A, 229th Assault Helicopter Battalion, 1st Cavalry Division (Airmobile)",
        "homeState": "Washington",
    },
    "dwight w. birdwell": {"posthumous": False},
    "gary m. rose": {"posthumous": False},
    "harold william bauer": {
        "actionPlace": "Guadalcanal, Solomon Islands",
        "unit": "Marine Fighting Squadron 212",
    },
    "richard i. bong": {
        "actionPlace": "over Borneo and Leyte, Philippine Islands",
        "unit": "49th Fighter Group, 5th Fighter Command, 5th Air Force",
    },
    "reinhardt john keppler": {
        "actionPlace": "off Savo Island, Solomon Islands",
        "unit": "U.S.S. San Francisco",
    },
    "ruben rivers": {
        "rank": "Staff Sergeant",
        "unit": "Company A, 761st Tank Battalion",
        "homeState": "Oklahoma",
    },
}


def _indexed_key(name_raw: str) -> str:
    return re.sub(r"\s+", " ", (name_raw or "").lstrip("*").strip()).upper()


def polish_citation(name_raw: str, citation: str | None) -> str:
    """Repair citation text that the Army index snapshot mistyped."""
    text = citation or ""
    key = _indexed_key(name_raw)
    if key.startswith("RIVERS, RUBEN"):
        return RIVERS_CITATION
    if key.startswith("CRANDALL, BRUCE"):
        text = text.replace("la Drang", "Ia Drang").replace("batallion", "battalion")
    if key.startswith("SPURRIER, JUNIOR"):
        text = (
            text.replace("S/Sergeant.", "S/Sgt.")
            .replace("Ml rifle", "M1 rifle")
            .replace("handgrenades", "hand grenades")
        )
    if key.startswith("MCCANDLESS, BRUCE"):
        text = text.replace(
            "the San Francisco was brought back",
            "the U.S.S. San Francisco was brought back",
        )
    return text.strip()


def apply_award_corrections(award: dict) -> None:
    name = (award.get("name") or "").lower()
    if name in NOT_POSTHUMOUS:
        award["posthumous"] = False
    overrides = FIELD_OVERRIDES.get(name)
    if not overrides:
        return
    for field, value in overrides.items():
        award[field] = value
