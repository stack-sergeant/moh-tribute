import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import test from "node:test";
import { basename } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";
import {
  DESCRIPTION_LIMIT,
  actionDatePhrase,
  birthDateValue,
  eraSlug,
  placeClause,
  recipientMetaDescription,
  recipientShareImagePath,
  recipientStructuredData,
  serializeJsonLd,
} from "../src/lib/recipient-meta.mjs";

const root = new URL("../", import.meta.url);
const people = JSON.parse(readFileSync(new URL("data/recipients.json", root), "utf8"));
const POSTHUMOUS = "Awarded posthumously.";

function person(id) {
  const found = people.find((item) => item.id === id);
  assert.ok(found, id);
  return found;
}

function description(id) {
  return recipientMetaDescription(person(id));
}

function walkStrings(value, visit) {
  if (typeof value === "string") visit(value);
  else if (Array.isArray(value)) value.forEach((item) => walkStrings(item, visit));
  else if (value && typeof value === "object") Object.values(value).forEach((item) => walkStrings(item, visit));
}

test("dates use one format and skip labels that are not dates", () => {
  assert.equal(actionDatePhrase({ actionDate: "1968-05-02", actionDateEnd: "1968-05-02" }), "2 May 1968");
  assert.equal(
    actionDatePhrase({ actionDate: "2004-11-10", actionDateEnd: "2004-11-10", actionDateLabel: "November 10, 2004" }),
    "10 November 2004",
  );
  assert.equal(
    actionDatePhrase({ actionDate: "1950-11-29", actionDateEnd: "1950-12-10" }),
    "29 November 1950 to 10 December 1950",
  );
  assert.equal(actionDatePhrase({ actionDate: "1942-04", actionDateEnd: "1942-04" }), "April 1942");
  assert.equal(
    actionDatePhrase({ actionDate: "1861-07-21", actionDateEnd: "1864-09" }),
    "21 July 1861 to September 1864",
  );
  assert.equal(actionDatePhrase({ actionDate: null, actionDateLabel: "Winter of 1872-73." }), "");
  assert.equal(actionDatePhrase({ actionDate: null, actionDateLabel: "Unknown, 1863-65." }), "");
});

test("places use in or near, and a leading direction does not become at", () => {
  assert.equal(placeClause("west of Loc Ninh, Cambodia"), "near Loc Ninh, Cambodia");
  assert.equal(placeClause("West of Da Nang, Republic of Vietnam"), "near Da Nang, Republic of Vietnam");
  assert.equal(
    placeClause("Northeast of Binarville, in the forest of Argonne, France"),
    "near Binarville, in the forest of Argonne, France",
  );
  assert.equal(placeClause("South Mountain, Maryland"), "in South Mountain, Maryland");
  assert.equal(placeClause("North Vietnam"), "in North Vietnam");
  assert.equal(placeClause("North Korea"), "in North Korea");
  assert.equal(placeClause("Off Okinawa"), "off Okinawa");
  assert.equal(placeClause("near Hawk Hill Fire Base, Quang Nam Province, Republic of Vietnam"), "near Hawk Hill Fire Base, Quang Nam Province, Republic of Vietnam");
  assert.equal(placeClause("Near, Padiglione, Italy"), "near Padiglione, Italy");
  assert.equal(placeClause("At, Arkansas"), "in Arkansas");
  assert.equal(placeClause(null), "");
  assert.equal(placeClause("Fort Wagner, S C,,"), "in Fort Wagner, S C");
});

test("Benavidez, Bellavia, and Petry descriptions use only their recorded facts", () => {
  const benavidez =
    "Roy P. Benavidez, Master Sergeant, U.S. Army, earned the Medal of Honor on 2 May 1968 near Loc Ninh, Cambodia (Vietnam War). Read the official citation.";
  const bellavia =
    "David G. Bellavia, Staff Sergeant, U.S. Army, earned the Medal of Honor on 10 November 2004 in Fallujah, Iraq (Iraq War). Read the official citation.";
  const petry =
    "Leroy A. Petry, Staff Sergeant, U.S. Army, earned the Medal of Honor on 26 May 2008 in Paktya Province, Afghanistan (War in Afghanistan).";
  assert.equal(description("roy-p-benavidez"), benavidez);
  assert.equal(description("david-g-bellavia"), bellavia);
  assert.equal(description("leroy-a-petry"), petry);
  for (const text of [benavidez, bellavia]) {
    assert.ok(text.length >= 140 && text.length <= DESCRIPTION_LIMIT, text.length);
  }
  assert.ok(petry.length <= DESCRIPTION_LIMIT);
  assert.equal(petry.includes("Read the official citation."), false);
  assert.equal(description("roy-p-benavidez").includes("posthumously"), false);
  assert.equal(description("john-r-fox").includes(POSTHUMOUS), false);
  assert.match(description("john-r-fox"), /Read the official citation\.$/);
  assert.equal(
    description("john-u-d-page"),
    "John U. D. Page, Lieutenant Colonel, U.S. Army, earned the Medal of Honor from 29 November 1950 to 10 December 1950 in Chosin Reservoir, Korea (Korean War).",
  );
  assert.match(description("dr-mary-e-walker"), /from 21 July 1861 to September 1864 \(Civil War\)\.$/);
  assert.equal(
    description("james-congdon"),
    "James Congdon, U.S. Army, earned the Medal of Honor (Civil War). Read the official citation.",
  );
});

test("every recipient description stays within 160 characters and is specific", () => {
  const descriptions = people.map((item) => recipientMetaDescription(item));
  const inRange = descriptions.filter((text) => text.length >= 140 && text.length <= DESCRIPTION_LIMIT).length;
  assert.equal(new Set(descriptions).size, descriptions.length);
  assert.ok(inRange >= 2700, `${inRange} descriptions are in the 140–160 range`);
  for (const [index, text] of descriptions.entries()) {
    const item = people[index];
    assert.ok(text.length <= DESCRIPTION_LIMIT, `${item.id} is ${text.length}`);
    assert.ok(text.length >= 80, `${item.id} is ${text.length}`);
    assert.match(text, /\.$/);
    assert.equal(text.includes("  "), false, text);
    assert.equal(text.includes(",,"), false, text);
    assert.equal(text.includes("()"), false, text);
    assert.equal(text.includes("undefined"), false, text);
    assert.equal(text.includes("nonprofit"), false, text);
    assert.equal(text.startsWith("Medal of Honor record for"), false);
    assert.equal(text.includes(" in ."), false, text);
    assert.equal(text.includes(" on ."), false, text);
    const leadPosthumous = Boolean(item.awards[0].posthumous);
    if (text.includes(POSTHUMOUS)) {
      assert.equal(leadPosthumous, true, item.id);
      assert.match(text, /Awarded posthumously\.$/);
    } else if (leadPosthumous) {
      assert.ok(text.length + ` ${POSTHUMOUS}`.length > DESCRIPTION_LIMIT, item.id);
    }
  }
});

test("era slugs match the existing era pages", () => {
  const eras = [...new Set(people.flatMap((item) => item.awards.map((award) => award.era)))];
  for (const era of eras) {
    const slug = eraSlug(era);
    assert.match(slug, /^[a-z0-9]+(?:-[a-z0-9]+)*$/);
    assert.equal(slug, era.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
  }
  assert.equal(eraSlug("Since 1975"), "since-1975");
  assert.equal(eraSlug("World War II"), "world-war-ii");
  assert.equal(eraSlug("Peacetime and other actions"), "peacetime-and-other-actions");
});

test("Person and BreadcrumbList JSON-LD use known facts and real site urls", () => {
  const origin = "https://valorrecord.com";
  const benavidez = person("roy-p-benavidez");
  const data = recipientStructuredData(benavidez, {
    origin,
    url: `${origin}/recipients/roy-p-benavidez`,
  });
  assert.equal(data["@context"], "https://schema.org");
  const [subject, crumbs] = data["@graph"];
  assert.equal(subject["@type"], "Person");
  assert.equal(subject.name, "Roy P. Benavidez");
  assert.equal(subject.url, "https://valorrecord.com/recipients/roy-p-benavidez");
  assert.equal(subject.award, "Medal of Honor");
  assert.equal(subject.jobTitle, "Master Sergeant");
  assert.equal(subject.memberOf["@type"], "Organization");
  assert.equal(subject.memberOf.name, "U.S. Army");
  assert.equal(subject.birthDate, "1935-08-05");
  assert.equal(subject.image, benavidez.photo.url);
  assert.equal(subject.deathDate, undefined);
  assert.equal(subject.description, description("roy-p-benavidez"));
  assert.equal(crumbs["@type"], "BreadcrumbList");
  assert.deepEqual(
    crumbs.itemListElement.map((item) => [item.position, item.name, item.item]),
    [
      [1, "Home", "https://valorrecord.com/"],
      [2, "Recipients", "https://valorrecord.com/recipients"],
      [3, "Vietnam War", "https://valorrecord.com/eras/vietnam-war"],
      [4, "Roy P. Benavidez", "https://valorrecord.com/recipients/roy-p-benavidez"],
    ],
  );

  const page = recipientStructuredData(person("john-u-d-page"), {
    origin,
    url: `${origin}/recipients/john-u-d-page`,
  });
  assert.equal(page["@graph"][0].image, "https://valorrecord.com/photos/john-u-d-page.jpg");
  assert.equal(page["@graph"][0].birthDate, "1904-02-08");
  assert.equal(page["@graph"][0].deathDate, undefined);
  assert.equal(page["@graph"][1].itemListElement[2].item, "https://valorrecord.com/eras/korean-war");

  const given = recipientStructuredData(person("john-j-given"), {
    origin,
    url: `${origin}/recipients/john-j-given`,
  });
  assert.equal(given["@graph"][0].image, undefined);

  const bellavia = recipientStructuredData(person("david-g-bellavia"), {
    origin,
    url: `${origin}/recipients/david-g-bellavia`,
  });
  assert.equal(bellavia["@graph"][0].image, "https://valorrecord.com/photos/david-g-bellavia.jpg");
  assert.equal(bellavia["@graph"][0].birthDate, undefined);
  assert.equal(bellavia["@graph"][1].itemListElement[2].name, "Since 1975");
  assert.equal(bellavia["@graph"][1].itemListElement[2].item, "https://valorrecord.com/eras/since-1975");

  const congdon = recipientStructuredData(person("james-congdon"), {
    origin,
    url: `${origin}/recipients/james-congdon`,
  });
  assert.equal(congdon["@graph"][0].jobTitle, undefined);
  assert.equal(birthDateValue(person("william-kyle-carpenter")), undefined);

  const escaped = serializeJsonLd({ name: "A < B" });
  assert.equal(escaped.includes("<"), false);
  assert.match(escaped, /\\u003c/);
  assert.deepEqual(JSON.parse(escaped), { name: "A < B" });
});

test("structured data stays valid for every recipient", () => {
  const origin = "https://valorrecord.com";
  for (const item of people) {
    const url = `${origin}/recipients/${item.id}`;
    const data = recipientStructuredData(item, { origin, url });
    const serialized = serializeJsonLd(data);
    assert.equal(serialized.includes("<"), false, item.id);
    const parsed = JSON.parse(serialized);
    const [subject, crumbs] = parsed["@graph"];
    assert.equal(parsed["@context"], "https://schema.org");
    assert.equal(subject["@type"], "Person");
    assert.equal(subject.name, item.name);
    assert.equal(subject.url, url);
    assert.equal(subject.award, "Medal of Honor");
    assert.equal(subject.memberOf.name, item.awards[0].branch);
    assert.equal(subject.description, recipientMetaDescription(item));
    if (item.awards[0].rank) assert.equal(subject.jobTitle, item.awards[0].rank.replace(/\s+/g, " ").trim());
    else assert.equal(subject.jobTitle, undefined);
    if (item.photo?.url) {
      assert.match(subject.image, /^https?:\/\//);
      assert.equal(subject.image.includes("/og/recipients/"), false);
    } else {
      assert.equal(subject.image, undefined);
    }
    assert.equal(subject.birthDate, birthDateValue(item));
    assert.equal(subject.deathDate, undefined);
    assert.equal(crumbs["@type"], "BreadcrumbList");
    const last = crumbs.itemListElement.at(-1);
    assert.equal(last.name, item.name);
    assert.equal(last.item, url);
    const eraCrumb = crumbs.itemListElement[2];
    assert.equal(eraCrumb.name, item.awards[0].era);
    assert.equal(eraCrumb.item, `${origin}/eras/${eraSlug(item.awards[0].era)}`);
    walkStrings(parsed, (text) => {
      assert.notEqual(text, "", item.id);
      assert.equal(text.includes("nonprofit"), false, item.id);
    });
    assert.equal(recipientShareImagePath(item), item.photo ? `/og/recipients/${item.id}.jpg` : null);
  }
});

function jpegSize(buf) {
  assert.equal(buf[0], 0xff);
  assert.equal(buf[1], 0xd8);
  let offset = 2;
  while (offset + 9 < buf.length) {
    assert.equal(buf[offset], 0xff);
    const marker = buf[offset + 1];
    if (marker === 0xc0 || marker === 0xc1 || marker === 0xc2) {
      return { height: buf.readUInt16BE(offset + 5), width: buf.readUInt16BE(offset + 7) };
    }
    const length = buf.readUInt16BE(offset + 2);
    assert.ok(length >= 2);
    offset += 2 + length;
  }
  throw new Error("JPEG size marker missing");
}

test("photo recipients have a 1200 by 630 share card and others keep the default", () => {
  const dir = new URL("public/og/recipients/", root);
  const files = new Set(readdirSync(dir).filter((name) => name.endsWith(".jpg")));
  const withPhoto = people.filter((item) => item.photo);
  assert.equal(files.size, withPhoto.length);
  for (const item of people) {
    const name = `${item.id}.jpg`;
    if (item.photo) assert.equal(files.has(name), true, item.id);
    else assert.equal(files.has(name), false, item.id);
  }
  for (const name of files) {
    const buf = readFileSync(new URL(name, dir));
    const size = jpegSize(buf);
    assert.equal(size.width, 1200, name);
    assert.equal(size.height, 630, name);
    assert.ok(buf.length <= 70_000, `${name} is ${buf.length} bytes`);
    assert.ok(buf.length >= 8_000, `${name} is ${buf.length} bytes`);
  }
  for (const id of ["david-g-bellavia", "william-kyle-carpenter", "roy-p-benavidez", "dr-mary-e-walker"]) {
    assert.equal(basename(recipientShareImagePath(person(id))), `${id}.jpg`);
  }
  assert.equal(recipientShareImagePath(person("john-u-d-page")), "/og/recipients/john-u-d-page.jpg");
  assert.equal(recipientShareImagePath(person("john-j-given")), null);
});

test("sample share cards contain the photograph, not a blank field", async () => {
  for (const id of ["william-kyle-carpenter", "david-g-bellavia", "roy-p-benavidez", "dr-mary-e-walker"]) {
    const stats = await sharp(fileURLToPath(new URL(`public/og/recipients/${id}.jpg`, root)))
      .extract({ left: 48, top: 36, width: 420, height: 540 })
      .stats();
    const variation = stats.channels.reduce((sum, channel) => sum + channel.stdev, 0);
    assert.ok(variation > 20, `${id} photo area looks blank (${variation.toFixed(1)})`);
  }
});
