/**
 * Recipient meta descriptions and JSON-LD.
 * Every clause comes from fields already on the recipient record.
 * Missing fields are omitted. Nothing is cut off mid-word.
 */

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const DESCRIPTION_LIMIT = 160;
const CTA = " Read the official citation.";
const POSTHUMOUS = " Awarded posthumously.";

function clean(value) {
  if (value == null) return "";
  return String(value).replace(/\s+/g, " ").trim();
}

function monthIndex(name) {
  const lower = String(name || "").toLowerCase();
  return MONTHS.findIndex((month) => month.toLowerCase() === lower);
}

function isRealDate(year, month, day) {
  if (year < 1700 || year > 2100 || month < 0 || month > 11) return false;
  const date = new Date(Date.UTC(year, month, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month && date.getUTCDate() === day;
}

function parseIsoDay(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);
  if (!isRealDate(year, month, day)) return null;
  return { year, month, day };
}

function parseIsoMonth(value) {
  const match = /^(\d{4})-(\d{2})$/.exec(value || "");
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  if (month < 0 || month > 11 || year < 1700 || year > 2100) return null;
  return { year, month };
}

function formatDay({ year, month, day }) {
  return `${day} ${MONTHS[month]} ${year}`;
}

function formatMonth({ year, month }) {
  return `${MONTHS[month]} ${year}`;
}

/**
 * One date style: "2 May 1968", "10 November 2004", "April 1942",
 * or a range joined with "to". Garbled source labels without an ISO
 * date are left off rather than repeated.
 */
export function actionDatePhrase(award) {
  const startDay = parseIsoDay(award?.actionDate);
  const endDay = parseIsoDay(award?.actionDateEnd);
  const startMonth = parseIsoMonth(award?.actionDate);
  const endMonth = parseIsoMonth(award?.actionDateEnd);

  if (startDay && endDay) {
    if (startDay.year === endDay.year && startDay.month === endDay.month && startDay.day === endDay.day) {
      return formatDay(startDay);
    }
    return `${formatDay(startDay)} to ${formatDay(endDay)}`;
  }
  if (startDay && endMonth) return `${formatDay(startDay)} to ${formatMonth(endMonth)}`;
  if (startDay) return formatDay(startDay);
  if (startMonth && endMonth) {
    const start = formatMonth(startMonth);
    const end = formatMonth(endMonth);
    return start === end ? start : `${start} to ${end}`;
  }
  if (startMonth) return formatMonth(startMonth);
  return "";
}

/**
 * "in" a recorded place. A place that begins with a compass direction
 * ("west of Loc Ninh") uses "near" and keeps the place name that follows.
 * A place that already starts with a preposition keeps that preposition.
 */
export function placeClause(place) {
  const value = clean(place)
    .replace(/\.+$/g, "")
    .replace(/,+/g, ",")
    .replace(/\s+,/g, ",")
    .replace(/,\s*/g, ", ")
    .replace(/,\s*$/g, "")
    .trim();
  if (!value) return "";
  const compass =
    /^(?:north(?:[-\s]?east|[-\s]?west)?|south(?:[-\s]?east|[-\s]?west)?|east|west)\s+of\s+(.+)$/i.exec(
      value,
    );
  if (compass) {
    const rest = compass[1].replace(/^,+/, "").trim();
    return rest ? `near ${rest}` : "";
  }
  const leading = /^(near|off|aboard|in|on|at)\b[\s,]+(.+)$/i.exec(value);
  if (leading) {
    const word = leading[1].toLowerCase() === "at" ? "in" : leading[1].toLowerCase();
    const rest = leading[2].replace(/^,+/, "").trim();
    return rest ? `${word} ${rest}` : "";
  }
  return `in ${value}`;
}

function sentence(parts) {
  const who = [parts.name, parts.rank, parts.branch].filter(Boolean);
  let text = `${who.join(", ")}, earned the Medal of Honor`;
  if (parts.when) {
    const prep = parts.when.includes(" to ") ? "from" : "on";
    text += ` ${prep} ${parts.when}`;
  }
  if (parts.where) text += ` ${parts.where}`;
  if (parts.context) text += ` (${parts.context})`;
  return `${text}.`;
}

export function recipientMetaDescription(person) {
  const award = person?.awards?.[0] ?? {};
  const full = {
    name: clean(person?.name),
    rank: clean(award.rank),
    branch: clean(award.branch),
    when: actionDatePhrase(award),
    where: placeClause(award.actionPlace),
    context: clean(award.conflict) || clean(award.era),
  };
  if (!full.name) return "Medal of Honor recipient.";

  let current = { ...full };
  let core = sentence(current);
  for (const key of ["context", "rank", "where", "when", "branch"]) {
    if (core.length <= DESCRIPTION_LIMIT) break;
    if (!current[key]) continue;
    current = { ...current, [key]: "" };
    core = sentence(current);
  }
  if (core.length > DESCRIPTION_LIMIT) {
    core = `${full.name} earned the Medal of Honor.`;
  }

  let text = core;
  if (text.length + CTA.length <= DESCRIPTION_LIMIT) text += CTA;
  if (award.posthumous && text.length + POSTHUMOUS.length <= DESCRIPTION_LIMIT) text += POSTHUMOUS;
  return text;
}

/** Same slug the era index and era pages already use. */
export function eraSlug(era) {
  return String(era || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function birthDateValue(person) {
  const text = clean(person?.birth);
  const dated = /\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b/.exec(text);
  if (dated) {
    const month = monthIndex(dated[2]);
    const day = Number(dated[1]);
    const year = Number(dated[3]);
    if (month >= 0 && isRealDate(year, month, day)) {
      return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    }
  }
  const yearInText = /\b(17\d{2}|18\d{2}|19\d{2}|20\d{2})\b/.exec(text);
  if (yearInText) return yearInText[1];
  const year = person?.birthYear;
  if (Number.isInteger(year) && year >= 1700 && year <= 2100) return String(year);
  return undefined;
}

function absoluteUrl(url, origin) {
  const value = clean(url);
  if (!value) return undefined;
  if (/^https?:\/\//i.test(value)) return value;
  const base = String(origin || "https://valorrecord.com").replace(/\/$/, "");
  return `${base}${value.startsWith("/") ? value : `/${value}`}`;
}

/** Self-hosted 1200×630 card. Null when the recipient has no photograph. */
export function recipientShareImagePath(person) {
  if (!clean(person?.photo?.url) || !clean(person?.id)) return null;
  return `/og/recipients/${person.id}.jpg`;
}

export function recipientStructuredData(person, { origin = "https://valorrecord.com", url } = {}) {
  const award = person?.awards?.[0] ?? {};
  const base = String(origin || "https://valorrecord.com").replace(/\/$/, "");
  const page = url || `${base}/recipients/${person.id}`;
  const personNode = {
    "@type": "Person",
    name: clean(person.name),
    url: page,
    award: "Medal of Honor",
  };
  const description = recipientMetaDescription(person);
  if (description) personNode.description = description;
  if (clean(award.branch)) {
    personNode.memberOf = { "@type": "Organization", name: clean(award.branch) };
  }
  if (clean(award.rank)) personNode.jobTitle = clean(award.rank);
  const birthDate = birthDateValue(person);
  if (birthDate) personNode.birthDate = birthDate;
  const image = absoluteUrl(person?.photo?.url, base);
  if (image) personNode.image = image;

  const era = clean(award.era);
  const crumbs = [
    { "@type": "ListItem", position: 1, name: "Home", item: `${base}/` },
    { "@type": "ListItem", position: 2, name: "Recipients", item: `${base}/recipients` },
  ];
  if (era) {
    crumbs.push({
      "@type": "ListItem",
      position: crumbs.length + 1,
      name: era,
      item: `${base}/eras/${eraSlug(era)}`,
    });
  }
  crumbs.push({
    "@type": "ListItem",
    position: crumbs.length + 1,
    name: clean(person.name),
    item: page,
  });

  return {
    "@context": "https://schema.org",
    "@graph": [
      personNode,
      { "@type": "BreadcrumbList", itemListElement: crumbs },
    ],
  };
}

export function serializeJsonLd(data) {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
