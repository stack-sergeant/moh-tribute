"""Corrections checked against CMOHS, the Army citation index, and NHHC.

The Army index snapshot mis-marks a few surviving recipients as posthumous,
and a handful of citation entries are truncated or mistyped. These overrides
keep a rebuild from putting that text back.
"""

from __future__ import annotations

import re

from mohlib import polish_prose

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

# CMOHS "Awarded Posthumously: No", or a later presentation after the recipient
# had already survived the action. The page uses this flag for "Gave his life",
# so a medal presented after a later death is not marked posthumous.
#
# Verified on https://www.cmohs.org/recipients/ unless noted.
NOT_POSTHUMOUS = {
    "bruce p. crandall",
    "dwight w. birdwell",
    "gary m. rose",
    # Awarded Posthumously: No. Presented 24 February 1981. Died 1998.
    "roy p. benavidez",
    # Awarded Posthumously: No. Living. Presented 3 January 2025.
    "kenneth j. david",
    # Awarded Posthumously: No. Presented 24 February 2026.
    "eric a. slover",
    # Survived Korea, died in 2017, medal presented 3 January 2025.
    # CMOHS says the presentation was posthumous. The 1953 action did not kill him.
    "richard e. cavazos",
    # Survived Korea, died 3 January 2020, medal presented 3 January 2025.
    # CMOHS Awarded Posthumously: Yes for that later presentation.
    "fred b. mcgee",
    # Survived the 1945 action, died 8 August 1985, medal presented 2 March 2026.
    # CMOHS Awarded Posthumously: Yes. https://www.cmohs.org/recipients/roderick-w-roddie-edmonds
    "roderick w. edmonds",
    # CMOHS lists no death and leaves Awarded Posthumously blank. Presented 2 March 2026.
    "terry p. richardson",
    # Awarded Posthumously: No. Presented 20 January 1998. Survived Okinawa.
    "james day",
}

# Died from the action. CMOHS Awarded Posthumously: Yes, and the death date
# is the action or the wounds from it.
POSTHUMOUS = {
    # Died 8 November 2005 of burns from 17 October 2005. The citation does not say he died.
    "alwyn c. cashe",
    # Died 17 January 1970. Citation: "laying down his own life".
    "donald p. sloat",
    # Died 12 July 2018. Citation: "cost him his life".
    "christopher a. celiz",
    # Died 22 April 2004 of wounds from 14 April 2004.
    "jason l. dunham",
    # Died 28 August 2013, the action date.
    "michael h. ollis",
    # Executed 18 June 1862 after the 12 April raid.
    "philip g. shadrach",
    "george d. wilson",
    # Died 12 June 1953 during the action.
    "charles r. johnson",
    # Died 5 June 1966, the action date.
    "hugh r. nelson jr.",
    # Died 18 May 1951. Citation: "fell mortally wounded".
    "wataru nakamura",
    # Died 15 February 1951. Citation: "was found dead beside his weapon".
    "bruno r. orig",
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
    # Army index: "At Danby's mills, Va., 6 February 1860."
    # CMOHS: 6 February 1865, Dabney's Mills, Virginia.
    # https://www.cmohs.org/recipients/john-c-delaney
    "john c. delaney": {
        "actionPlace": "Dabney's Mills, Virginia",
        "actionDate": "1865-02-06",
        "actionDateEnd": "1865-02-06",
        "actionDateLabel": "6 February 1865",
        "actionYear": 1865,
    },
    # Army index action date 26 April 1872, Place: Platte River, Nebraska.
    # CMOHS names the same action at the Loupe Fork, 26 April 1872.
    # https://www.cmohs.org/recipients/william-frederick-buffalo-bill-cody
    "william f. cody": {
        "rank": "Civilian Scout",
        "unit": "3rd Cavalry, U.S. Army",
        "actionPlace": "Loupe Fork of the Platte River, Nebraska",
        "actionDate": "1872-04-26",
        "actionDateEnd": "1872-04-26",
        "actionDateLabel": "26 April 1872",
        "actionYear": 1872,
    },
    # Army index: Place: Washita River, Texas. Date: 12 September 1874.
    # Rank: Scout (Civilian). Organization: 6th U.S. Cavalry.
    "amos chapman": {
        "rank": "Scout",
        "unit": "6th U.S. Cavalry",
        "actionPlace": "Washita River, Texas",
        "actionDate": "1874-09-12",
        "actionDateEnd": "1874-09-12",
        "actionDateLabel": "12 September 1874",
        "actionYear": 1874,
    },
    # Army index: Place: Wichita River, Texas. Action date: 12 September 1874.
    # Rank: Scout. Organization: 6th U.S. Cavalry.
    "william dixon": {
        "rank": "Scout",
        "unit": "6th U.S. Cavalry",
        "actionPlace": "Wichita River, Texas",
        "actionDate": "1874-09-12",
        "actionDateEnd": "1874-09-12",
        "actionDateLabel": "12 September 1874",
        "actionYear": 1874,
    },
    # Army index: Place: Holliday Creek, Texas. Date: 5 October 1870.
    # Rank: Post Guide during Indian Wars.
    "james b. doshier": {
        "rank": "Post Guide",
        "actionPlace": "Holliday Creek, Texas",
        "actionDate": "1870-10-05",
        "actionDateEnd": "1870-10-05",
        "actionDateLabel": "5 October 1870",
        "actionYear": 1870,
    },
    # Army index "Places and dates" runs from Bull Run, 21 July 1861, through
    # the Battle of Atlanta, September 1864. 10 June 1977 is the restoration.
    # The index lists several places across the war, so one place is not stored.
    "dr mary e. walker": {
        "actionPlace": None,
        "actionDate": "1861-07-21",
        "actionDateEnd": "1864-09",
        "actionDateLabel": "21 July 1861 – September 1864",
        "actionYear": 1861,
    },
    # CMOHS action place. The citation says "a mission in Venezuela" and does not name the city.
    # https://www.cmohs.org/recipients/eric-a-slover
    "eric a. slover": {
        "actionPlace": "Caracas, Venezuela",
        "unit": "160th Special Operations Aviation Regiment (Airborne)",
    },
    # The general order names only the country. CMOHS names the place.
    # https://www.cmohs.org/recipients/donald-p-sloat
    "donald p. sloat": {
        "actionPlace": "near Hawk Hill Fire Base, Quang Nam Province, Republic of Vietnam",
    },
    # CMOHS: west of Loc Ninh, Cambodia. The citation OCR says "Loe Ninh".
    # https://www.cmohs.org/recipients/roy-p-benavidez
    "roy p. benavidez": {
        "actionPlace": "west of Loc Ninh, Cambodia",
        "unit": "Detachment B-56, 5th Special Forces Group (Airborne), 1st Special Forces",
    },
}


def _indexed_key(name_raw: str) -> str:
    return re.sub(r"\s+", " ", (name_raw or "").lstrip("*").strip()).upper()


def polish_citation(name_raw: str, citation: str | None) -> str:
    """Repair citation text that the Army index snapshot mistyped."""
    text = polish_prose(citation or "")
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
    if name in POSTHUMOUS:
        award["posthumous"] = True
    overrides = FIELD_OVERRIDES.get(name)
    if not overrides:
        return
    for field, value in overrides.items():
        award[field] = value
