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
