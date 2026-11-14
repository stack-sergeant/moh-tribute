/**
 * Render public/og.png, the 1200×630 link-preview card.
 *
 * Source photograph: "Into the Jaws of Death"
 * (Into_the_Jaws_of_Death_23-0455M_edit.jpg), Chief Photographer's Mate
 * Robert F. Sargent, U.S. Coast Guard, 6 June 1944. Public domain,
 * U.S. National Archives. The homepage still shows that photograph and
 * keeps its credit. This script only builds the self-hosted card.
 *
 * Type is Oswald, the site's display face (SIL Open Font License,
 * scripts/assets/fonts/OFL.txt).
 *
 *   node scripts/render-og.mjs
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const sourcePath = join(root, "scripts/assets/into-the-jaws-of-death.jpg");
const semiPath = join(root, "scripts/assets/fonts/Oswald-SemiBold.ttf");
const mediumPath = join(root, "scripts/assets/fonts/Oswald-Medium.ttf");
const outPath = join(root, "public/og.png");

const WIDTH = 1200;
const HEIGHT = 630;
/** Keep the landing craft, the soldiers in the surf, and a band of sky. */
const CROP_TOP = 460;
const BYTE_BUDGET = 150_000;

const INK = "#f4efe4";
const GOLD = "#d4b36a";
const BLACK = "#07080b";

function fontFace(family, filePath) {
  const data = readFileSync(filePath).toString("base64");
  return `@font-face { font-family: '${family}'; src: url('data:font/ttf;base64,${data}') format('truetype'); }`;
}

function overlay() {
  const titleSize = 66;
  const subSize = 28;
  return Buffer.from(`<svg width="${WIDTH}" height="${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style><![CDATA[
      ${fontFace("Oswald Semi", semiPath)}
      ${fontFace("Oswald Med", mediumPath)}
    ]]></style>
    <linearGradient id="shade" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0%" stop-color="${BLACK}" stop-opacity="0.94"/>
      <stop offset="18%" stop-color="${BLACK}" stop-opacity="0.84"/>
      <stop offset="38%" stop-color="${BLACK}" stop-opacity="0.36"/>
      <stop offset="64%" stop-color="${BLACK}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="${WIDTH}" height="${HEIGHT}" fill="url(#shade)"/>
  <rect x="72" y="456" width="64" height="3" fill="${GOLD}"/>
  <text x="72" y="530" font-family="Oswald Semi" font-size="${titleSize}" letter-spacing="${(0.12 * titleSize).toFixed(2)}" fill="${INK}">VALOR RECORD</text>
  <text x="72" y="580" font-family="Oswald Med" font-size="${subSize}" letter-spacing="0.4" fill="${GOLD}">Every Medal of Honor recipient. Every story.</text>
</svg>`);
}

async function renderCard() {
  const meta = await sharp(sourcePath).metadata();
  if (!meta.width || !meta.height) throw new Error("Could not read the source photograph.");
  const cropHeight = Math.round((meta.width * HEIGHT) / WIDTH);
  if (CROP_TOP + cropHeight > meta.height) {
    throw new Error(`Crop ${cropHeight}px from y=${CROP_TOP} does not fit the ${meta.height}px source.`);
  }
  const photo = await sharp(sourcePath)
    .extract({ left: 0, top: CROP_TOP, width: meta.width, height: cropHeight })
    .resize(WIDTH, HEIGHT, { kernel: "lanczos3" })
    .toBuffer();
  return sharp(photo).composite([{ input: overlay() }]).png().toBuffer();
}

async function compress(raw) {
  const attempts = [
    { quality: 64, dither: 0.5 },
    { quality: 60, dither: 0.55 },
    { quality: 58, dither: 0.6 },
    { quality: 56, dither: 0.65 },
    { quality: 52, dither: 0.7 },
    { quality: 48, dither: 0.75 },
  ];
  let best = null;
  for (const attempt of attempts) {
    const buf = await sharp(raw)
      .png({
        compressionLevel: 9,
        palette: true,
        quality: attempt.quality,
        effort: 10,
        dither: attempt.dither,
        colors: 256,
      })
      .toBuffer();
    const fits = buf.length <= BYTE_BUDGET;
    const better =
      fits &&
      (!best ||
        attempt.quality > best.quality ||
        (attempt.quality === best.quality && buf.length < best.buf.length));
    if (better) best = { buf, quality: attempt.quality, dither: attempt.dither };
  }
  if (!best) throw new Error(`Could not fit og.png under ${BYTE_BUDGET} bytes.`);
  const info = await sharp(best.buf).metadata();
  if (info.width !== WIDTH || info.height !== HEIGHT) {
    throw new Error(`Expected ${WIDTH}×${HEIGHT}, got ${info.width}×${info.height}.`);
  }
  console.log(`palette quality ${best.quality}, dither ${best.dither}`);
  return best.buf;
}

const raw = await renderCard();
const png = await compress(raw);
writeFileSync(outPath, png);
console.log(`Wrote ${outPath} (${png.length} bytes, ${WIDTH}×${HEIGHT})`);
