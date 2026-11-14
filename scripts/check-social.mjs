import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  DEFAULT_SOCIAL_ALT,
  DEFAULT_SOCIAL_HEIGHT,
  DEFAULT_SOCIAL_WIDTH,
  isWikimediaHotlink,
  resolveSocialImage,
} from "../src/lib/social-image.mjs";

const origin = "https://valorrecord.com";
const root = new URL("../", import.meta.url);
const jaws =
  "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a5/Into_the_Jaws_of_Death_23-0455M_edit.jpg/1920px-Into_the_Jaws_of_Death_23-0455M_edit.jpg";

function pngSize(buf) {
  assert.equal(buf.subarray(12, 16).toString("ascii"), "IHDR");
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

test("the shared card is a 1200 by 630 png under the size budget", () => {
  const png = readFileSync(new URL("public/og.png", root));
  const size = pngSize(png);
  assert.equal(size.width, DEFAULT_SOCIAL_WIDTH);
  assert.equal(size.height, DEFAULT_SOCIAL_HEIGHT);
  assert.ok(png.length <= 150_000, `og.png is ${png.length} bytes`);
  assert.match(DEFAULT_SOCIAL_ALT, /Every Medal of Honor recipient\. Every story\./);
});

test("pages without their own image use the absolute card url", () => {
  assert.equal(resolveSocialImage(undefined, origin), "https://valorrecord.com/og.png");
  assert.equal(resolveSocialImage("  ", origin), "https://valorrecord.com/og.png");
});

test("wikimedia hotlinks never become the social image", () => {
  assert.equal(isWikimediaHotlink(jaws), true);
  assert.equal(resolveSocialImage(jaws, origin), "https://valorrecord.com/og.png");
  assert.equal(
    resolveSocialImage(
      "https://upload.wikimedia.org/wikipedia/commons/a/a5/Into_the_Jaws_of_Death_23-0455M_edit.jpg",
      origin,
    ),
    "https://valorrecord.com/og.png",
  );
  assert.equal(
    resolveSocialImage("//commons.wikimedia.org/wiki/Special:FilePath/Into_the_Jaws_of_Death_23-0455M_edit.jpg", origin),
    "https://valorrecord.com/og.png",
  );
});

test("a self-hosted portrait stays an absolute url on this site", () => {
  assert.equal(
    resolveSocialImage("/photos/david-g-bellavia.jpg", origin),
    "https://valorrecord.com/photos/david-g-bellavia.jpg",
  );
  assert.equal(
    resolveSocialImage("https://valorrecord.com/photos/david-g-bellavia.jpg", origin),
    "https://valorrecord.com/photos/david-g-bellavia.jpg",
  );
});

test("the homepage still credits the Coast Guard photograph", () => {
  const imagery = readFileSync(new URL("src/lib/imagery.ts", root), "utf8");
  assert.match(imagery, /Chief Photographer's Mate Robert F\. Sargent, U\.S\. Coast Guard/);
  const home = readFileSync(new URL("src/pages/index.astro", root), "utf8");
  assert.match(home, /heroScene\.credit/);
  assert.match(home, /heroScene\.sourceUrl/);
});
