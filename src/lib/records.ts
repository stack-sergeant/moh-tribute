import battles from "../../data/battles.json";
import recipients from "../../data/recipients.json";
import stats from "../../data/stats.json";

export interface Photo {
  url: string;
  pageUrl: string;
  license: string;
  licenseUrl?: string | null;
  credit: string;
  width?: number;
  height?: number;
}

export interface Award {
  awardId: string;
  rank: string | null;
  unit: string | null;
  branch: string;
  conflict: string;
  era: string;
  actionPlace: string | null;
  actionDate: string | null;
  actionDateEnd: string | null;
  actionDateLabel: string | null;
  actionYear: number | null;
  posthumous: boolean;
  citation: string;
  issueDate: string | null;
  generalOrder: string | null;
  sourceUrl: string;
  sourceLabel: string;
  extraSources: string[];
  nameNotes: string[];
  battleId: string | null;
}

export interface Recipient {
  id: string;
  name: string;
  nameSort: string;
  last: string;
  first: string;
  homeState: string | null;
  birth: string | null;
  birthYear: number | null;
  awards: Award[];
  photo: Photo | null;
  wikipedia: string | null;
  wikidataId: string | null;
}

export interface MediaLink {
  kind: string;
  title: string;
  url: string;
  publisher: string;
  note: string;
}

export interface Battle {
  id: string;
  title: string;
  conflict: string;
  era: string;
  dateLabel: string;
  location: string | null;
  summary: string;
  curated: boolean;
  media: MediaLink[];
  recipientIds: string[];
}

export const allRecipients = recipients as Recipient[];
export const allBattles = battles as Battle[];
export const datasetStats = stats;

const recipientById = new Map(allRecipients.map((person) => [person.id, person]));
const battleById = new Map(allBattles.map((battle) => [battle.id, battle]));

export function recipient(id: string) {
  return recipientById.get(id);
}

export function battle(id: string) {
  return battleById.get(id);
}

export function conflicts() {
  return Object.keys(datasetStats.byConflict);
}

export function branches() {
  return Object.keys(datasetStats.byBranch);
}

export function states() {
  return [...new Set(allRecipients.map((person) => person.homeState).filter(Boolean) as string[])].sort();
}

export function eras() {
  return Object.entries(datasetStats.byEra).filter(([, count]) => count > 0);
}

export function eraSlug(era: string) {
  return era.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function actLine(citation: string) {
  const text = citation.replace(/\s+/g, " ").trim();
  const stripped = text.replace(
    /^for conspicuous gallantry and intrepidity[^.]{0,240}?\.\s*/i,
    "",
  );
  const source = stripped.length > 48 ? stripped : text;
  const sentence = source.split(/(?<=\.)\s+/)[0] ?? source;
  if (sentence.length <= 170) return sentence;
  return `${sentence.slice(0, 160).replace(/\s+\S*$/, "")}…`;
}

export function storyLabel(name: string) {
  return name === "Mary Edwards Walker" ? "Read her story" : "Read his story";
}

export function gaveLifeLabel(name: string) {
  return name === "Mary Edwards Walker" ? "Gave her life" : "Gave his life";
}

const ordered = [...allRecipients].sort((a, b) => a.nameSort.localeCompare(b.nameSort));
const orderIndex = new Map(ordered.map((person, index) => [person.id, index]));

export function neighbors(id: string) {
  const index = orderIndex.get(id);
  if (index == null) return { prev: undefined, next: undefined };
  return { prev: ordered[index - 1], next: ordered[index + 1] };
}

export function featuredPool() {
  const buckets = new Map<string, Recipient[]>();
  const ranked = [...allRecipients]
    .filter((person) => person.photo)
    .sort((a, b) => b.awards[0].citation.length - a.awards[0].citation.length);
  for (const person of ranked) {
    const era = person.awards[0].era;
    const bucket = buckets.get(era) ?? [];
    if (bucket.length >= 6) continue;
    bucket.push(person);
    buckets.set(era, bucket);
  }
  return [...buckets.values()].flat();
}
