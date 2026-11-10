# Valor Record

An unofficial public archive of recorded Medal of Honor recipients. The name lives in `src/site.ts` and can be changed in that one file.

The site is not affiliated with the Department of Defense, any military service, the Congressional Medal of Honor Society, or the National Medal of Honor Museum. It does not use the medal or an official seal as a logo.

## What a page contains

Each recipient has a profile with name, rank, branch, unit, conflict, action date, action place, and the official citation. A photograph is shown only when a public-domain or Creative Commons Wikimedia file matched that person, with the license and credit on the page. Otherwise the page says that no verified public-domain photo is on file yet.

Battle and action pages list the recipients tied to that place. Nine hubs are curated by hand across different eras, with checked links to articles, footage, books, and films. Footage is linked, not copied. Every other place named in the citation index has its own page, including actions with one recipient.

Search and filters cover name, conflict, branch, home state, and whether the source marks the award as posthumous.

## Counts in this build

| | |
| --- | --- |
| People | 3,497 |
| Awards | 3,514 |
| People with more than one award in this dataset | 17 |
| Verified reusable photographs | 1,349 (38.6%) |
| Action pages | 1,626, of which 9 are curated |

Public totals are usually given as more than 3,500 awards, and about 3,526 people after the January 3, 2025 ceremony, with further awards in 2026. This archive is close to that range and is not a complete official roll. Gaps are listed on the About page: rescinded 1917 awards are omitted on purpose; some recent Navy and Marine Corps awards are not in the Army general orders used here; a few general-order PDFs did not extract into clean text; and some citation-index entries could not be parsed.

Curated hubs and the number of recipients matched from the citation text:

- Battle of Gettysburg (Civil War) — 61
- Belleau Wood (World War I) — 4
- The Lost Battalion in the Argonne (World War I) — 6
- Battle of Iwo Jima (World War II) — 27
- Chosin Reservoir (Korean War) — 11
- Battle of Ia Drang (Vietnam War) — 3
- Battle of Mogadishu (Somalia) — 2
- Battle of Kamdesh (Afghanistan) — 2
- Second Battle of Fallujah (Iraq War) — 1

## Data pipeline

Citations are U.S. government works. The compiler reads snapshots in `data/raw/army/` of the Army citation index at <https://www.army.mil/medalofhonor/recipients.html>. That index includes Navy, Marine Corps, Air Force, and Coast Guard awards. Later awards are added from Army general orders when the recipient is not already in the index. Photographs come from Wikidata and Wikimedia Commons, and files that are fair use or non-commercial are dropped.

```bash
python3 scripts/download_citations.py   # optional refresh from the Internet Archive
python3 scripts/enrich_photos.py        # optional; writes data/photos.json
SKIP_AGO_FETCH=1 python3 scripts/build_dataset.py
```

`scripts/build_dataset.py` writes `data/recipients.json`, `data/battles.json`, `data/awards.csv`, and `data/stats.json`. Wikipedia prose is not copied. Portraits and narrative text are not taken from the Congressional Medal of Honor Society, the National Medal of Honor Museum, Home of Heroes, Military Times, or Honoring American Troops.

## Render static site

| Setting | Value |
| --- | --- |
| Build command | `npm ci && npm run build` |
| Publish directory | `dist` |

```bash
npm ci
npm run build
npm run preview
```

The same values are in `render.yaml`.
