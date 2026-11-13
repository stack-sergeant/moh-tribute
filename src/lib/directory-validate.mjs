/** Shared checks for the directory data files. Imported by the site and by node:test. */

export const VETCERT_URL = "https://veterans.certify.sba.gov/";

export const DISCLOSURE = "This is a paid placement. It is not an endorsement by Valor Record.";

export const US_STATES = [
  ["AL", "Alabama"],
  ["AK", "Alaska"],
  ["AZ", "Arizona"],
  ["AR", "Arkansas"],
  ["CA", "California"],
  ["CO", "Colorado"],
  ["CT", "Connecticut"],
  ["DE", "Delaware"],
  ["DC", "District of Columbia"],
  ["FL", "Florida"],
  ["GA", "Georgia"],
  ["HI", "Hawaii"],
  ["ID", "Idaho"],
  ["IL", "Illinois"],
  ["IN", "Indiana"],
  ["IA", "Iowa"],
  ["KS", "Kansas"],
  ["KY", "Kentucky"],
  ["LA", "Louisiana"],
  ["ME", "Maine"],
  ["MD", "Maryland"],
  ["MA", "Massachusetts"],
  ["MI", "Michigan"],
  ["MN", "Minnesota"],
  ["MS", "Mississippi"],
  ["MO", "Missouri"],
  ["MT", "Montana"],
  ["NE", "Nebraska"],
  ["NV", "Nevada"],
  ["NH", "New Hampshire"],
  ["NJ", "New Jersey"],
  ["NM", "New Mexico"],
  ["NY", "New York"],
  ["NC", "North Carolina"],
  ["ND", "North Dakota"],
  ["OH", "Ohio"],
  ["OK", "Oklahoma"],
  ["OR", "Oregon"],
  ["PA", "Pennsylvania"],
  ["RI", "Rhode Island"],
  ["SC", "South Carolina"],
  ["SD", "South Dakota"],
  ["TN", "Tennessee"],
  ["TX", "Texas"],
  ["UT", "Utah"],
  ["VT", "Vermont"],
  ["VA", "Virginia"],
  ["WA", "Washington"],
  ["WV", "West Virginia"],
  ["WI", "Wisconsin"],
  ["WY", "Wyoming"],
];

export const BRANCHES = ["Air Force", "Army", "Coast Guard", "Marine Corps", "Multiple", "National Guard", "Navy", "Space Force"];

export const MUSEUM_CATEGORIES = [
  "Air Force museum",
  "Army museum",
  "Coast Guard museum",
  "Heritage center",
  "Historic ship",
  "Marine Corps museum",
  "National Guard museum",
  "National military museum",
  "Navy museum",
  "Veterans museum",
];

const STATE_NAMES = new Map(US_STATES);

export function stateName(code) {
  const name = STATE_NAMES.get(code);
  if (!name) throw new Error(`Unknown state code: ${code}`);
  return name;
}

export function slugify(value) {
  return String(value)
    .toLowerCase()
    .replaceAll("&", " and ")
    .replaceAll(/[^a-z0-9]+/g, "-")
    .replaceAll(/^-|-$/g, "");
}

export function stateSlug(code) {
  return slugify(stateName(code));
}

export function verificationBadge(kind) {
  if (kind === "sba-vetcert") return "SBA VetCert verified";
  if (kind === "sam-veteran-owned") return "Registered in SAM as veteran-owned";
  throw new Error(`Unknown veteran-owned verification: ${kind}`);
}

export function veteranStatusLabel(kind) {
  if (kind === "veteran") return "Veteran";
  if (kind === "service-disabled-veteran") return "Service-disabled veteran";
  throw new Error(`Unknown veteran status: ${kind}`);
}

/** External sponsor links are paid placements. Internal placeholder links are not. */
export function sponsorLinkRel(href) {
  if (typeof href === "string" && /^https?:\/\//i.test(href)) return "sponsored noopener";
  return undefined;
}

function isHttps(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:";
  } catch {
    return false;
  }
}

const FORBIDDEN = ["email", "contactemail", "contact_email", "phone", "uei", "ein", "duns", "hours"];

function forbiddenKey(record) {
  return Object.keys(record).find((key) => FORBIDDEN.includes(key.toLowerCase()));
}

export function validateDirectory({ museums, businesses, sponsor }) {
  const errors = [];
  if (!Array.isArray(museums) || museums.length === 0) errors.push("museums must be a non-empty array");
  if (!Array.isArray(businesses)) errors.push("businesses must be an array");
  if (!sponsor || typeof sponsor !== "object") errors.push("sponsor must be an object");

  const slugs = new Set();
  let us = 0;
  let overseas = 0;
  for (const museum of Array.isArray(museums) ? museums : []) {
    const where = museum?.name || museum?.slug || "museum";
    if (!museum.slug || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(museum.slug)) errors.push(`${where}: slug`);
    if (slugs.has(museum.slug)) errors.push(`${where}: duplicate slug`);
    slugs.add(museum.slug);
    if (!museum.name || museum.name.length > 180) errors.push(`${where}: name`);
    if (!museum.city || museum.city.length > 80) errors.push(`${where}: city`);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(museum.lastChecked || "")) errors.push(`${where}: lastChecked`);
    if (!BRANCHES.includes(museum.branch)) errors.push(`${where}: branch`);
    if (!MUSEUM_CATEGORIES.includes(museum.category)) errors.push(`${where}: category`);
    if (!Array.isArray(museum.sources) || museum.sources.length === 0) errors.push(`${where}: source`);
    for (const source of museum.sources || []) {
      if (!source.label || !isHttps(source.url)) errors.push(`${where}: source URL`);
    }
    if (museum.website && !isHttps(museum.website)) errors.push(`${where}: website`);
    if (museum.description && (typeof museum.description !== "string" || museum.description.length > 140)) {
      errors.push(`${where}: description`);
    }
    const banned = forbiddenKey(museum);
    if (banned) errors.push(`${where}: do not store ${banned}`);
    if (/lorem ipsum|example business|acme\b/i.test(museum.name)) errors.push(`${where}: placeholder name`);
    if (museum.country === "United States") {
      us += 1;
      if (!STATE_NAMES.has(museum.state)) errors.push(`${where}: state`);
      else if (museum.region !== stateSlug(museum.state)) errors.push(`${where}: region slug`);
    } else if (museum.region !== "overseas" || museum.state) {
      errors.push(`${where}: overseas region`);
    } else {
      overseas += 1;
      if (!museum.country) errors.push(`${where}: country`);
    }
  }
  if (us === 0 || overseas === 0) errors.push("directory needs both U.S. and overseas museums");

  const businessSlugs = new Set();
  for (const business of Array.isArray(businesses) ? businesses : []) {
    const where = business?.name || business?.slug || "business";
    if (!business.slug || businessSlugs.has(business.slug)) errors.push(`${where}: slug`);
    businessSlugs.add(business.slug);
    if (!business.name || /lorem ipsum|example business|acme\b|your veteran-owned business/i.test(business.name)) {
      errors.push(`${where}: name`);
    }
    try {
      veteranStatusLabel(business.veteranStatus);
      verificationBadge(business.verification);
    } catch (error) {
      errors.push(`${where}: ${error.message}`);
    }
    if (!business.city || !business.category || !business.branch || !business.country) errors.push(`${where}: place`);
    if (!business.description || business.description.length > 400) errors.push(`${where}: description`);
    if (!isHttps(business.website)) errors.push(`${where}: website`);
    if (business.country === "United States" && !STATE_NAMES.has(business.state)) errors.push(`${where}: state`);
    const banned = forbiddenKey(business);
    if (banned) errors.push(`${where}: do not publish ${banned}`);
  }

  if (sponsor && typeof sponsor === "object") {
    if (sponsor.disclosure !== DISCLOSURE) errors.push("sponsor disclosure");
    if (sponsor.label !== "Sponsored") errors.push("sponsor label");
    if (sponsor.kicker !== "Featured sponsor") errors.push("sponsor kicker");
    if (!sponsor.title || !sponsor.action) errors.push("sponsor copy");
    if (typeof sponsor.href !== "string" || !sponsor.href.startsWith("/")) {
      if (!(typeof sponsor.href === "string" && isHttps(sponsor.href))) errors.push("sponsor href");
    }
  }
  return errors;
}
