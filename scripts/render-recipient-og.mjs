/**
 * Build a 1200×630 share card for every recipient who has a photograph.
 *
 * The photograph is only resized and placed, letterboxed on a branded
 * background so the whole picture stays visible. Nothing is generated,
 * filtered, or cropped into the likeness. The recipient page keeps the
 * original credit and license; a short credit is repeated on the card.
 *
 * Cards are written to public/og/recipients and copied into the site as-is.
 * Render does not run this script. Regenerate when a photograph changes:
 *
 *   node scripts/render-recipient-og.mjs
 *   node scripts/render-recipient-og.mjs --force roy-p-benavidez
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";
import recipients from "../data/recipients.json" with { type: "json" };

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "public/og/recipients");
const semiPath = join(root, "scripts/assets/fonts/Oswald-SemiBold.ttf");
const mediumPath = join(root, "scripts/assets/fonts/Oswald-Medium.ttf");

const WIDTH = 1200;
const HEIGHT = 630;
const COLUMN = 548;
const BOX_W = 500;
const BOX_H = 586;
const TEXT_X = 608;
const TEXT_W = WIDTH - TEXT_X - 48;
const BYTE_BUDGET = 70_000;
const RULE_Y = 96;
const RULE_H = 3;
const EYEBROW_SIZE = 18;
const EYEBROW_BASELINE = 136;
// Oswald round capitals reach 820/1000 of the em. Text y is the baseline,
// so the name starts one eyebrow-gap below the label plus that cap height.
const CAP_RATIO = 820 / 1000;

const INK = "#f4efe4";
const MUTED = "#c8bfb0";
const GOLD = "#d4b36a";
const NAVY = "#0c1824";
const BLACK = "#07080b";

const args = process.argv.slice(2);
const force = args.includes("--force");
const only = new Set(args.filter((arg) => !arg.startsWith("--")));

function fontFace(family, filePath) {
  const data = readFileSync(filePath).toString("base64");
  return `@font-face { font-family: '${family}'; src: url('data:font/ttf;base64,${data}') format('truetype'); }`;
}

const fontCss = `${fontFace("Oswald Semi", semiPath)}${fontFace("Oswald Med", mediumPath)}`;

function xmlEscape(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function approxWidth(text, fontSize) {
  let width = 0;
  for (const char of text) {
    const factor = /[ilI1.,'`|!]/.test(char) ? 0.28 : /[MWmwOQ@%]/.test(char) ? 0.68 : 0.5;
    width += fontSize * factor;
  }
  return width;
}

// librsvg does not apply the embedded face, so it draws whatever fontconfig
// resolves for "Oswald Semi". Wrapping uses the wider of that font and the
// estimate above, so a line stays inside the card.
function resolvedAdvances() {
  let file;
  try {
    file = execFileSync("fc-match", ["-f", "%{file}", "Oswald Semi"], { encoding: "utf8" }).trim();
  } catch {
    return null;
  }
  try {
    return readAdvances(readFileSync(file));
  } catch {
    return null;
  }
}

function readAdvances(data) {
  const u16 = (offset) => data.readUInt16BE(offset);
  const u32 = (offset) => data.readUInt32BE(offset);
  const i16 = (offset) => data.readInt16BE(offset);
  const numTables = u16(4);
  const tables = new Map();
  for (let i = 0; i < numTables; i++) {
    const base = 12 + i * 16;
    tables.set(data.toString("latin1", base, base + 4), u32(base + 8));
  }
  const unitsPerEm = u16(tables.get("head") + 18);
  const numHMetrics = u16(tables.get("hhea") + 34);
  const hmtx = tables.get("hmtx");
  const glyphAdvance = [];
  for (let i = 0; i < numHMetrics; i++) glyphAdvance.push(u16(hmtx + i * 4));
  const cmap = tables.get("cmap");
  const encodings = u16(cmap + 2);
  let subtable = null;
  for (let i = 0; i < encodings; i++) {
    const record = cmap + 4 + i * 8;
    const offset = cmap + u32(record + 4);
    if (u16(offset) === 4) subtable = offset;
  }
  if (subtable == null) return null;
  const segCount = u16(subtable + 6) / 2;
  const endCount = subtable + 14;
  const startCount = endCount + segCount * 2 + 2;
  const idDelta = startCount + segCount * 2;
  const idRangeOffset = idDelta + segCount * 2;
  const advances = new Map();
  for (let i = 0; i < segCount; i++) {
    const end = u16(endCount + i * 2);
    const start = u16(startCount + i * 2);
    const delta = i16(idDelta + i * 2);
    const range = u16(idRangeOffset + i * 2);
    for (let code = start; code <= end && code < 0xffff; code++) {
      let glyph = range === 0 ? (code + delta) & 0xffff : u16(idRangeOffset + i * 2 + range + (code - start) * 2);
      if (range !== 0 && glyph !== 0) glyph = (glyph + delta) & 0xffff;
      if (glyph === 0) continue;
      const units = glyph < numHMetrics ? glyphAdvance[glyph] : glyphAdvance[numHMetrics - 1];
      advances.set(code, units / unitsPerEm);
    }
  }
  return advances;
}

const drawnAdvances = resolvedAdvances();

function drawnWidth(text, fontSize) {
  if (!drawnAdvances) return 0;
  let width = 0;
  for (const char of text) {
    const advance = drawnAdvances.get(char.codePointAt(0));
    width += (advance ?? 0.5) * fontSize;
  }
  return width;
}

function textWidth(text, fontSize) {
  return Math.max(approxWidth(text, fontSize), drawnWidth(text, fontSize));
}

function wrapToWidth(text, fontSize, maxWidth, measure = approxWidth) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (current && measure(next, fontSize) > maxWidth) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  return lines;
}

function fitLines(text, { size, min, maxLines, width }) {
  let fontSize = size;
  let lines = wrapToWidth(text, fontSize, width, textWidth);
  while (lines.length > maxLines && fontSize > min) {
    fontSize -= 1;
    lines = wrapToWidth(text, fontSize, width, textWidth);
  }
  return { fontSize, lines };
}

function nameBaseline(fontSize) {
  const ruleBottom = RULE_Y + RULE_H;
  const eyebrowTop = EYEBROW_BASELINE - EYEBROW_SIZE * CAP_RATIO;
  const gap = eyebrowTop - ruleBottom;
  return Math.round(EYEBROW_BASELINE + gap + fontSize * CAP_RATIO);
}

function compactCredit(credit) {
  let text = String(credit || "").replace(/\s+/g, " ").trim();
  text = text.replace(/\s*(This image was released|This tag does not indicate|See Commons:Licensing).*/i, "");
  text = text.replace(/[.\s]+$/g, "").trim();
  if (!text) return "";
  if (text.length <= 86) return text;
  const cut = text.slice(0, 86);
  const space = cut.lastIndexOf(" ");
  const shortened = (space > 40 ? cut.slice(0, space) : cut).replace(/[.,;:\s]+$/g, "");
  return `${shortened}…`;
}

function textSvg(person) {
  const award = person.awards[0] ?? {};
  const nameFit = fitLines(person.name, { size: 52, min: 32, maxLines: 3, width: TEXT_W });
  const rankFit = award.rank
    ? fitLines(award.rank, { size: 26, min: 18, maxLines: 3, width: TEXT_W })
    : { fontSize: 26, lines: [] };
  const branch = award.branch ? [award.branch] : [];
  const license = /cc\s*by/i.test(person.photo?.license || "") ? person.photo.license : "";
  const credit = compactCredit(person.photo?.credit);
  const creditLines = credit ? wrapToWidth(credit, 16, TEXT_W).slice(0, 2) : [];

  const blocks = [];
  let y = nameBaseline(nameFit.fontSize);
  for (const line of nameFit.lines) {
    blocks.push(lineText(line, y, nameFit.fontSize, INK, "Oswald Semi", 0));
    y += nameFit.fontSize + 8;
  }
  y += 10;
  for (const line of rankFit.lines) {
    blocks.push(lineText(line, y, rankFit.fontSize, MUTED, "Oswald Med", 0));
    y += rankFit.fontSize + 6;
  }
  for (const line of branch) {
    y += 6;
    blocks.push(lineText(line, y, 24, GOLD, "Oswald Med", 0));
    y += 30;
  }

  const footer = [];
  let footerY = HEIGHT - 36 - (creditLines.length - 1) * 20;
  if (license) footerY -= 22;
  if (license) {
    footer.push(lineText(license, footerY, 16, GOLD, "Oswald Med", 0.04));
    footerY += 22;
  }
  creditLines.forEach((line, index) => {
    footer.push(lineText(line, footerY + index * 20, 16, MUTED, "Oswald Med", 0));
  });

  return Buffer.from(`<svg width="${WIDTH}" height="${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs><style><![CDATA[${fontCss}]]></style></defs>
  <text x="${TEXT_X}" y="78" font-family="Oswald Med" font-size="18" letter-spacing="3.2" fill="${GOLD}">VALOR RECORD</text>
  <rect x="${TEXT_X}" y="${RULE_Y}" width="64" height="${RULE_H}" fill="${GOLD}"/>
  <text x="${TEXT_X}" y="${EYEBROW_BASELINE}" font-family="Oswald Semi" font-size="${EYEBROW_SIZE}" letter-spacing="2.6" fill="${INK}">MEDAL OF HONOR</text>
  ${blocks.join("\n  ")}
  ${footer.join("\n  ")}
</svg>`);
}

function lineText(line, y, size, fill, family, trackingEm) {
  const tracking = (trackingEm * size).toFixed(2);
  return `<text x="${TEXT_X}" y="${y}" font-family="${family}" font-size="${size}" letter-spacing="${tracking}" fill="${fill}">${xmlEscape(line)}</text>`;
}

function frameSvg(left, top, width, height) {
  return Buffer.from(`<svg width="${WIDTH}" height="${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <rect x="${left + 1}" y="${top + 1}" width="${Math.max(0, width - 2)}" height="${Math.max(0, height - 2)}" fill="none" stroke="${GOLD}" stroke-width="2"/>
</svg>`);
}

const panel = Buffer.from(`<svg width="${WIDTH}" height="${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <rect width="${COLUMN}" height="${HEIGHT}" fill="${NAVY}"/>
</svg>`);

let backgroundPromise;
function background() {
  backgroundPromise ??= sharp({
    create: { width: WIDTH, height: HEIGHT, channels: 3, background: BLACK },
  })
    .png()
    .toBuffer();
  return backgroundPromise;
}

function localSource(url) {
  if (url.startsWith("/")) return join(root, "public", url);
  try {
    const parsed = new URL(url);
    if (parsed.hostname === "valorrecord.com" || parsed.hostname === "www.valorrecord.com") {
      return join(root, "public", decodeURIComponent(parsed.pathname));
    }
  } catch {
    return null;
  }
  return null;
}

let cooldownUntil = 0;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchRemote(url) {
  let lastError;
  for (let attempt = 1; attempt <= 6; attempt += 1) {
    const pause = cooldownUntil - Date.now();
    if (pause > 0) await sleep(pause);
    try {
      const response = await fetch(url, {
        headers: {
          "User-Agent": "ValorRecord/1.0 (https://valorrecord.com) recipient-share-card",
          Accept: "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
        redirect: "follow",
        signal: AbortSignal.timeout(45_000),
      });
      if (response.status === 429 || response.status >= 500) {
        const retryAfter = Number(response.headers.get("retry-after"));
        const wait = Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter * 1000 : 12_000 * attempt;
        cooldownUntil = Math.max(cooldownUntil, Date.now() + wait);
        throw new Error(`HTTP ${response.status}`);
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return Buffer.from(await response.arrayBuffer());
    } catch (error) {
      lastError = error;
      if (!String(error.message).includes("429")) await sleep(700 * attempt);
    }
  }
  throw lastError;
}

function isReady(filePath) {
  try {
    const buf = readFileSync(filePath);
    if (buf.length < 1000 || buf[0] !== 0xff || buf[1] !== 0xd8) return false;
    let offset = 2;
    while (offset + 9 < buf.length) {
      if (buf[offset] !== 0xff) return false;
      const marker = buf[offset + 1];
      if (marker === 0xc0 || marker === 0xc1 || marker === 0xc2) {
        return buf.readUInt16BE(offset + 5) === HEIGHT && buf.readUInt16BE(offset + 7) === WIDTH;
      }
      const length = buf.readUInt16BE(offset + 2);
      if (length < 2) return false;
      offset += 2 + length;
    }
  } catch {
    return false;
  }
  return false;
}

async function encode(raw) {
  let best = null;
  for (const quality of [70, 62, 54, 46, 38]) {
    const buf = await sharp(raw).jpeg({ quality, mozjpeg: true, chromaSubsampling: "4:2:0" }).toBuffer();
    best = buf;
    if (buf.length <= BYTE_BUDGET) break;
  }
  const info = await sharp(best).metadata();
  if (info.width !== WIDTH || info.height !== HEIGHT) {
    throw new Error(`Expected ${WIDTH}×${HEIGHT}, got ${info.width}×${info.height}.`);
  }
  return best;
}

async function renderPerson(person) {
  const source = localSource(person.photo.url);
  const input = source ? readFileSync(source) : await fetchRemote(person.photo.url);
  const fitted = await sharp(input, { failOn: "none" })
    .rotate()
    .flatten({ background: NAVY })
    .resize({
      width: BOX_W,
      height: BOX_H,
      fit: "inside",
      withoutEnlargement: false,
      kernel: "lanczos3",
    })
    .toBuffer();
  const meta = await sharp(fitted).metadata();
  const left = Math.max(0, Math.round((COLUMN - meta.width) / 2));
  const top = Math.max(0, Math.round((HEIGHT - meta.height) / 2));
  const raw = await sharp(await background())
    .composite([
      { input: panel },
      { input: fitted, left, top },
      { input: frameSvg(left, top, meta.width, meta.height) },
      { input: textSvg(person) },
    ])
    .png()
    .toBuffer();
  return encode(raw);
}

async function pool(items, limit, worker) {
  const queue = items.slice();
  let cursor = 0;
  const errors = [];
  async function run() {
    while (cursor < queue.length) {
      const index = cursor;
      cursor += 1;
      const person = queue[index];
      try {
        await worker(person, index);
      } catch (error) {
        errors.push(`${person.id}: ${error.message}`);
      }
    }
  }
  await Promise.all(Array.from({ length: limit }, () => run()));
  return errors;
}

mkdirSync(outDir, { recursive: true });
const people = recipients.filter((person) => person.photo && (!only.size || only.has(person.id)));
if (only.size && people.length !== only.size) {
  const found = new Set(people.map((person) => person.id));
  const missing = [...only].filter((id) => !found.has(id));
  console.error(`No photograph for: ${missing.join(", ")}`);
  process.exit(1);
}

let written = 0;
let skipped = 0;
const started = Date.now();
const errors = await pool(people, 2, async (person, index) => {
  const outPath = join(outDir, `${person.id}.jpg`);
  if (!force && isReady(outPath)) {
    skipped += 1;
  } else {
    const jpeg = await renderPerson(person);
    writeFileSync(outPath, jpeg);
    written += 1;
  }
  if ((index + 1) % 50 === 0 || index + 1 === people.length) {
    const elapsed = ((Date.now() - started) / 1000).toFixed(0);
    console.log(`${index + 1}/${people.length} (${written} written, ${skipped} kept, ${elapsed}s)`);
  }
});

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
const bytes = people.reduce((sum, person) => sum + statSync(join(outDir, `${person.id}.jpg`)).size, 0);
console.log(
  `Done. ${people.length} cards, ${written} written, ${skipped} already current, ${(bytes / 1024 / 1024).toFixed(1)} MB`,
);
