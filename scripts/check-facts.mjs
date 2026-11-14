import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { battleDocumentTitle, recipientDocumentTitle } from "../src/lib/page-title.mjs";

const root = new URL("../", import.meta.url);
const people = JSON.parse(readFileSync(new URL("data/recipients.json", root), "utf8"));
const battles = JSON.parse(readFileSync(new URL("data/battles.json", root), "utf8"));

function person(id) {
  const found = people.find((item) => item.id === id);
  assert.ok(found, id);
  return found;
}

test("Benavidez and David did not give their lives", () => {
  assert.equal(person("roy-p-benavidez").awards[0].posthumous, false);
  assert.equal(person("kenneth-j-david").awards[0].posthumous, false);
});

test("Cashe, Sloat, and Celiz are posthumous", () => {
  assert.equal(person("alwyn-c-cashe").awards[0].posthumous, true);
  assert.equal(person("donald-p-sloat").awards[0].posthumous, true);
  assert.equal(person("christopher-a-celiz").awards[0].posthumous, true);
});

test("Dunham is recorded as Marine Corps", () => {
  assert.equal(person("jason-l-dunham").awards[0].branch, "U.S. Marine Corps");
});

test("recipient and battle document titles are unique", () => {
  const recipientTitles = people.map((item) => recipientDocumentTitle(item, people));
  const battleTitles = battles.map((item) => battleDocumentTitle(item, battles));
  assert.equal(new Set(recipientTitles).size, recipientTitles.length);
  assert.equal(new Set(battleTitles).size, battleTitles.length);
});
