import businessesData from "../../data/directory/businesses.json";
import museumsData from "../../data/directory/museums.json";
import sponsorData from "../../data/directory/sponsor.json";
import {
  slugify,
  sponsorLinkRel,
  stateName,
  stateSlug,
  US_STATES,
  validateDirectory,
  verificationBadge,
  veteranStatusLabel,
  VETCERT_URL,
} from "./directory-validate.mjs";

export interface MuseumSource {
  label: string;
  url: string;
}

export interface Museum {
  slug: string;
  name: string;
  city: string;
  state?: string;
  country: string;
  region: string;
  branch: string;
  category: string;
  website?: string;
  sources: MuseumSource[];
  lastChecked: string;
  description?: string;
}

export interface Business {
  slug: string;
  name: string;
  veteranStatus: "veteran" | "service-disabled-veteran";
  branch: string;
  website: string;
  city: string;
  state: string;
  country: string;
  category: string;
  description: string;
  verification: "sba-vetcert" | "sam-veteran-owned";
}

export interface Sponsor {
  kicker: string;
  label: string;
  title: string;
  action: string;
  href: string;
  disclosure: string;
}

export const museums = museumsData as Museum[];
export const businesses = businessesData as Business[];
export const sponsor = sponsorData as Sponsor;

const directoryErrors = validateDirectory({ museums, businesses, sponsor });
if (directoryErrors.length) {
  throw new Error(`Directory data is not publishable:\n${directoryErrors.join("\n")}`);
}

export { slugify, sponsorLinkRel, stateName, stateSlug, US_STATES, verificationBadge, veteranStatusLabel, VETCERT_URL };

export const imlsCitation =
  "Frehill, L. M. and Pelczar, M. (2018). Data File Documentation: Museum Data Files, FY 2018 Release. Institute of Museum and Library Services: Washington, DC.";

export const imlsDataUrl = "https://www.imls.gov/research-evaluation/data/museum-data-files";

const env = import.meta.env as Record<string, string | undefined>;
export const formEndpoint = (env.PUBLIC_DIRECTORY_FORM_ENDPOINT ?? "").trim();

export const checkedOn = museums.reduce(
  (latest, museum) => (museum.lastChecked > latest ? museum.lastChecked : latest),
  museums[0].lastChecked,
);

export function formatDay(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-US", {
    timeZone: "UTC",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export function regionLabel(region: string): string {
  if (region === "overseas") return "Overseas";
  for (const [code] of US_STATES as [string, string][]) {
    if (stateSlug(code) === region) return stateName(code);
  }
  return region;
}

export function placeLabel(museum: Museum): string {
  if (museum.country === "United States" && museum.state) return `${museum.city}, ${stateName(museum.state)}`;
  return `${museum.city}, ${museum.country}`;
}

export function blurb(museum: Museum): string {
  const kind = museum.category.toLowerCase();
  const article = /^[aeiou]/.test(kind) ? "an" : "a";
  return `${museum.name} is ${article} ${kind} in ${placeLabel(museum)}.`;
}

export function metaDescription(text: string): string {
  if (text.length <= 160) return text;
  return `${text.slice(0, 157).trimEnd()}...`;
}

export function museumHref(museum: Museum): string {
  return `/directory/museums/${museum.region}/${museum.slug}`;
}

export function businessRegion(business: Business): string {
  if (business.country === "United States") return stateSlug(business.state);
  return slugify(business.country);
}

export function businessHref(business: Business): string {
  return `/directory/businesses/${businessRegion(business)}/${business.slug}`;
}

export function businessAreaLabel(business: Business): string {
  if (business.country === "United States") return stateName(business.state);
  return business.country;
}

export function placeKey(museum: Museum): string {
  if (museum.region === "overseas") return `overseas:${slugify(museum.country)}`;
  return museum.region;
}

export function sameUrl(left?: string, right?: string): boolean {
  if (!left || !right) return false;
  return left.replace(/\/$/, "") === right.replace(/\/$/, "");
}

export function imlsOnly(museum: Museum): boolean {
  return museum.sources.every((source) => source.label.includes("IMLS"));
}

export function museumsInRegion(region: string): Museum[] {
  return museums
    .filter((museum) => museum.region === region)
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function regionLinks(): { href: string; label: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const museum of museums) counts.set(museum.region, (counts.get(museum.region) ?? 0) + 1);
  return [...counts.entries()]
    .map(([region, count]) => ({
      href: `/directory/museums/${region}`,
      label: regionLabel(region),
      count,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export function placeFilters(): { value: string; label: string }[] {
  const states = new Map<string, string>();
  const countries = new Set<string>();
  for (const museum of museums) {
    if (museum.region === "overseas") countries.add(museum.country);
    else states.set(museum.region, regionLabel(museum.region));
  }
  const domestic = [...states.entries()]
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([value, label]) => ({ value, label }));
  const abroad = [...countries]
    .sort((a, b) => a.localeCompare(b))
    .map((country) => ({ value: `overseas:${slugify(country)}`, label: country }));
  return [...domestic, ...abroad];
}

export function optionList(values: string[]): string[] {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b));
}

export function overseasGroups(): { country: string; museums: Museum[] }[] {
  const groups = new Map<string, Museum[]>();
  for (const museum of museumsInRegion("overseas")) {
    const list = groups.get(museum.country) ?? [];
    list.push(museum);
    groups.set(museum.country, list);
  }
  return [...groups.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([country, list]) => ({ country, museums: list }));
}

export const businessBranches = ["Army", "Navy", "Marine Corps", "Air Force", "Coast Guard", "Space Force", "Multiple"];

export const businessCategories = [
  "Construction",
  "Food and drink",
  "Healthcare",
  "Manufacturing",
  "Professional services",
  "Retail",
  "Trades",
  "Transportation",
  "Other",
];
