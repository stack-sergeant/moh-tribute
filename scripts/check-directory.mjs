import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  FOUNDING_RATE,
  sponsorLinkRel,
  validateDirectory,
  verificationBadge,
} from "../src/lib/directory-validate.mjs";

const root = new URL("../", import.meta.url);

function readJson(path) {
  return JSON.parse(readFileSync(new URL(path, root), "utf8"));
}

const museums = readJson("data/directory/museums.json");
const businesses = readJson("data/directory/businesses.json");
const sponsor = readJson("data/directory/sponsor.json");

test("directory data files are publishable", () => {
  const errors = validateDirectory({ museums, businesses, sponsor });
  assert.deepEqual(errors, []);
});

test("launch ships with no business listings", () => {
  assert.equal(businesses.length, 0);
});

test("verification badges stay distinct", () => {
  assert.equal(verificationBadge("sba-vetcert"), "SBA VetCert verified");
  assert.equal(verificationBadge("sam-veteran-owned"), "Registered in SAM as veteran-owned");
});

test("sponsor links are marked only when they leave the site", () => {
  assert.equal(sponsorLinkRel("https://example.com/offer"), "sponsored noopener");
  assert.equal(sponsorLinkRel("/directory/sponsor"), undefined);
  assert.equal(sponsor.href, "/directory/sponsor");
  assert.equal(sponsor.rate, FOUNDING_RATE);
  assert.equal(sponsor.disclosure, "This is a paid placement. It is not an endorsement by Valor Record.");
});

test("every museum has a source and the set covers both maps", () => {
  assert.ok(museums.some((museum) => museum.country === "United States"));
  assert.ok(museums.some((museum) => museum.region === "overseas"));
  for (const museum of museums) {
    assert.ok(museum.sources.some((source) => source.url.startsWith("https://")));
  }
});
