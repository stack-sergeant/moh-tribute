export interface Cadence {
  id: string;
  src: string;
  title: string;
  playerLabel: string;
  branch: string;
  caller: string;
  unit: string;
  recorded: string;
  place: string;
  credit: string;
  virin: string;
  sourceUrl: string;
  license: string;
  clip: string;
}

const license =
  "U.S. government work. The DVIDS record is marked public domain and does not note copyrighted music. Works prepared by U.S. government employees as part of their official duties are not eligible for copyright protection in the United States.";

export const cadences: Cadence[] = [
  {
    id: "johnson-left-my-home",
    src: "/audio/johnson-left-my-home.mp3",
    title: "I Left My Home",
    playerLabel: "I Left My Home — Staff Sgt. Anisha Johnson",
    branch: "Army",
    caller: "Drill Sergeant (Staff Sgt.) Anisha Johnson",
    unit: "Delta Battery, 1st Battalion, 19th Field Artillery",
    recorded: "3 August 2020",
    place: "Fort Sill, Oklahoma",
    credit: "Video by Marie Pihulic, Fort Sill Public Affairs",
    virin: "200803-A-GO806-426",
    sourceUrl: "https://www.dvidshub.net/video/777613/cadence-competition-drill-sgt-johnson",
    license,
    clip: "Opening verse only (about 52 seconds), through the call to join the Army. Later verses in the same recording were left off.",
  },
  {
    id: "bouchard-airborne-ranger",
    src: "/audio/bouchard-airborne-ranger.mp3",
    title: "Airborne Ranger",
    playerLabel: "Airborne Ranger — Sgt. Brian Bouchard",
    branch: "Army",
    caller: "Drill Sergeant (Sgt.) Brian Bouchard",
    unit: "Echo Battery, 1st Battalion, 79th Field Artillery, Basic Combat Training",
    recorded: "3 August 2020",
    place: "Fort Sill, Oklahoma",
    credit: "Video by Marie Pihulic, Fort Sill Public Affairs",
    virin: "200803-A-GO806-773",
    sourceUrl: "https://www.dvidshub.net/video/777616/cadence-competition-drill-sgt-bouchard",
    license,
    clip: "About 73 seconds, ending on the Airborne Ranger response. This is an artillery drill sergeant calling that cadence, not a recording of an Airborne or Ranger unit. Later verses in the same video were left off.",
  },
  {
    id: "moses-lock-and-load",
    src: "/audio/moses-lock-and-load.mp3",
    title: "Lock and Load",
    playerLabel: "Lock and Load — Staff Sgt. Chris Moses",
    branch: "Army",
    caller: "Drill Sergeant (Staff Sgt.) Chris Moses",
    unit: "Echo Battery, 1st Battalion, 31st Field Artillery Regiment",
    recorded: "3 August 2020",
    place: "Fort Sill, Oklahoma",
    credit: "Video by Marie Pihulic, Fort Sill Public Affairs",
    virin: "200803-A-GO806-090",
    sourceUrl: "https://www.dvidshub.net/video/777617/cadence-competition-drill-sgt-moses",
    license,
    clip: "Opening of the call (about 70 seconds).",
  },
  {
    id: "wilcox-bandits",
    src: "/audio/wilcox-bandits.mp3",
    title: "Bandits Lead the Way",
    playerLabel: "Bandits Lead the Way — Staff Sgt. Tamika Wilcox",
    branch: "Army",
    caller: "Drill Sergeant (Staff Sgt.) Tamika Wilcox",
    unit: "Bravo Battery, 1st Battalion, 31st Field Artillery, Basic Combat Training",
    recorded: "3 August 2020",
    place: "Fort Sill, Oklahoma",
    credit: "Video by Marie Pihulic, Fort Sill Public Affairs",
    virin: "200803-A-GO806-331",
    sourceUrl: "https://www.dvidshub.net/video/777618/cadence-competition-drill-sgt-wilcox",
    license,
    clip: "The “Bandits lead the way” opening joined to the later “this army life is crazy” verses (about 89 seconds). One verse between those sections was left off.",
  },
  {
    id: "marines-di-contest",
    src: "/audio/marines-di-contest.mp3",
    title: "Best Damn Cadence Calling Contest",
    playerLabel: "Cadence contest — San Diego drill instructors",
    branch: "Marine Corps",
    caller: "Drill instructors at the West Coast Drill Instructor Association reunion",
    unit: "Marine Corps Recruit Depot San Diego",
    recorded: "16 September 2016",
    place: "San Diego, California",
    credit: "Video by Lance Cpl. Kailey Maraglia, Marine Corps Recruit Depot San Diego",
    virin: "160916-M-CF555-714",
    sourceUrl: "https://www.dvidshub.net/video/485738/drill-instructor-cadence-calling-contest",
    license,
    clip: "A portion of the calling contest (about 56 seconds).",
  },
];
