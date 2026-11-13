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
| People | 3,503 |
| Awards | 3,520 |
| Verified reusable photographs | 1,418 (40.5%) |
| Action pages | 1,626, of which 9 are curated |

Public totals are usually given as more than 3,500 awards, and about 3,526 people after the January 3, 2025 ceremony, with further awards in 2026. This archive is close to that range and is not a complete official roll. Gaps are listed on the About page. Rescinded 1917 awards are omitted on purpose. James Capers Jr., John W. Ripley, Elmer Royce Williams, and Nicholas Dockery were added from Army, Navy, and DVIDS releases. The Unknown Americans of World War II and Korea come from the Army special-legislation page. Williams’s entry uses the Navy’s published account of the action because that release does not print a separate full citation.

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

## Directory

`/directory` lists military museums and veteran-owned businesses. Businesses are published only after someone opts in and a person approves the submission. Do not import SAM.gov extracts, and do not scrape SAM.gov or SBA VetCert. A reviewer may open [SBA VetCert](https://veterans.certify.sba.gov/) or SAM while checking one submission. The public badge is either `SBA VetCert verified` or `Registered in SAM as veteran-owned`.

Museums are facts in `data/directory/museums.json`: name, city, state or country, branch, category, website when one was checked, source URL, and `lastChecked`. U.S. rows that cite IMLS use the public-domain FY 2018 Museum Data Files. Cite them as: Frehill, L. M. and Pelczar, M. (2018). Data File Documentation: Museum Data Files, FY 2018 Release. Institute of Museum and Library Services: Washington, DC. Other rows use official service lists or the museum's own site. Do not paste prose or photographs from those sites. One neutral sentence is allowed in an optional `description` of 140 characters or fewer. Leave it off when you do not need it.

`data/directory/businesses.json` ships as an empty array. `npm test` includes a check that the array is still empty for this launch. Delete that one test when the first approved business is added. To publish a reviewed business, add one object and rebuild:

```json
{
  "slug": "river-city-machine",
  "name": "River City Machine",
  "veteranStatus": "veteran",
  "branch": "Army",
  "website": "https://example.com",
  "city": "Columbus",
  "state": "OH",
  "country": "United States",
  "category": "Manufacturing",
  "description": "One sentence written for this listing.",
  "verification": "sba-vetcert"
}
```

`veteranStatus` is `veteran` or `service-disabled-veteran`. `verification` is `sba-vetcert` or `sam-veteran-owned`. Do not store the contact email, phone, or UEI. `state` is the USPS code when the country is United States. For another country, put the country in `country` and a short region code in `state` only if you also change the validator; otherwise keep non-U.S. businesses out until that field is agreed. The template above is not a live listing. Do not commit a placeholder business.

The sponsor card and footer bar read `data/directory/sponsor.json`. The launch copy is a placeholder that links to `/directory/sponsor`. Keep `label` as `Sponsored`, `kicker` as `Featured sponsor`, and `disclosure` as `This is a paid placement. It is not an endorsement by Valor Record.` When a real sponsor is approved, set `title` and `action`, and set `href` to the sponsor URL. An `https` href is rendered with `rel="sponsored noopener"`.

### Submission forms

`/directory/submit` and `/directory/sponsor` post to `PUBLIC_DIRECTORY_FORM_ENDPOINT` when that variable is present at build time. A Formspree-style URL such as `https://formspree.io/f/yourFormId` works. The honeypot field is `_gotcha`. Leave the variable unset until the review inbox is chosen. The forms then say submissions open soon and the submit button stays disabled. Do not point the form at a personal email address.

```bash
PUBLIC_DIRECTORY_FORM_ENDPOINT=https://formspree.io/f/yourFormId npm run build
```

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

The same values are in `render.yaml`. That file also sets response headers so `sitemap.xml` is served as XML and `robots.txt` as plain text.

## Search engines

The production build writes `dist/sitemap.xml` from the pages it just generated. Every URL is `https://valorrecord.com/...` and includes a `lastmod` of the git commit being built. While the archive is under 50,000 URLs, that file is the sitemap. Above that limit it becomes a sitemap index, and the URLs are split across `sitemap-1.xml`, `sitemap-2.xml`, and so on.

`public/robots.txt` allows every crawler and points to `https://valorrecord.com/sitemap.xml`.

Canonical and social tags use those same page URLs, without a trailing slash except on the homepage. A recipient page uses that person's public-domain photograph when one is already on the page. Every other page uses the public-domain D-Day photograph already shown on the homepage.
