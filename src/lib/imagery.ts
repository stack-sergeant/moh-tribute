export interface Scene {
  url: string;
  alt: string;
  credit: string;
  license: string;
  sourceUrl: string;
}

/**
 * Public-domain or CC BY photographs. Credits were read from Wikimedia Commons.
 * The homepage still shows the hero file below and prints its credit.
 * Link previews use the self-hosted card at /og.png, rendered from this photograph
 * by scripts/render-og.mjs. Crawlers are refused by the Wikimedia thumbnail host.
 */
export const heroScene: Scene = {
  url: "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a5/Into_the_Jaws_of_Death_23-0455M_edit.jpg/1920px-Into_the_Jaws_of_Death_23-0455M_edit.jpg",
  alt: "U.S. soldiers wade from a Coast Guard landing craft toward Omaha Beach on D-Day, 6 June 1944.",
  credit: "Chief Photographer's Mate Robert F. Sargent, U.S. Coast Guard",
  license: "Public domain",
  sourceUrl: "https://commons.wikimedia.org/wiki/File:Into_the_Jaws_of_Death_23-0455M_edit.jpg",
};

export const eraScenes: { era: string; title: string; scene: Scene }[] = [
  {
    era: "Civil War",
    title: "Civil War",
    scene: {
      url: "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/86/The_Battle_of_Gettysburg.jpg/1920px-The_Battle_of_Gettysburg.jpg",
      alt: "A 19th-century print of the Battle of Gettysburg.",
      credit: "Internet Archive Book Images, via Wikimedia Commons",
      license: "No restrictions",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:The_Battle_of_Gettysburg.jpg",
    },
  },
  {
    era: "Indian Wars",
    title: "Indian Wars",
    scene: {
      url: "https://upload.wikimedia.org/wikipedia/commons/1/1f/Buffalo_Soldiers_25th_Infantry_1890_%2830337519457%29.jpg",
      alt: "Buffalo Soldiers of the 25th Infantry in 1890.",
      credit: "U.S. Army photograph, via the National Park Service and Wikimedia Commons",
      license: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Buffalo_Soldiers_25th_Infantry_1890_(30337519457).jpg",
    },
  },
  {
    era: "World War I",
    title: "World War I",
    scene: {
      url: "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/bb/168th_Infantry_-_French_and_American_raiding_party%2C_Badonviller%2C_France%2C_March_17%2C_1918.jpg/1920px-168th_Infantry_-_French_and_American_raiding_party%2C_Badonviller%2C_France%2C_March_17%2C_1918.jpg",
      alt: "A French and American raiding party of the 168th Infantry in France, 17 March 1918.",
      credit: "U.S. Army Signal Corps",
      license: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:168th_Infantry_-_French_and_American_raiding_party,_Badonviller,_France,_March_17,_1918.jpg",
    },
  },
  {
    era: "World War II",
    title: "World War II",
    scene: {
      url: "https://upload.wikimedia.org/wikipedia/commons/7/74/LVT_and_landing_craft_from_USS_Sanborn_%28APA-193%29_off_Iwo_Jima_1945.jpg",
      alt: "Landing craft and tracked vehicles from USS Sanborn off Iwo Jima in 1945.",
      credit: "Lt. Howard W. Whalen, U.S. Naval Reserve",
      license: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:LVT_and_landing_craft_from_USS_Sanborn_(APA-193)_off_Iwo_Jima_1945.jpg",
    },
  },
  {
    era: "Korean War",
    title: "Korea",
    scene: {
      url: "https://upload.wikimedia.org/wikipedia/commons/1/16/1st_Marine_Division_at_Chosin_Reservoir_in_Korea%2C_December_1950.jpg",
      alt: "Marines of the 1st Marine Division at the Chosin Reservoir in December 1950.",
      credit: "U.S. Marine Corps",
      license: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:1st_Marine_Division_at_Chosin_Reservoir_in_Korea,_December_1950.jpg",
    },
  },
  {
    era: "Vietnam War",
    title: "Vietnam",
    scene: {
      url: "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/fc/UH-1D_helicopters_in_Vietnam_1966.jpg/1920px-UH-1D_helicopters_in_Vietnam_1966.jpg",
      alt: "U.S. Army UH-1D helicopters in Vietnam in 1966.",
      credit: "Sgt. 1st Class James K. F. Dung, U.S. Army",
      license: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:UH-1D_helicopters_in_Vietnam_1966.jpg",
    },
  },
  {
    era: "Since 1975",
    title: "War on Terror",
    scene: {
      url: "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/83/Flickr_-_The_U.S._Army_-_Soldiers_on_patrol_in_Korengal_Valley.jpg/1920px-Flickr_-_The_U.S._Army_-_Soldiers_on_patrol_in_Korengal_Valley.jpg",
      alt: "U.S. Army soldiers on patrol in the Korengal Valley, Afghanistan.",
      credit: "U.S. Army",
      license: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Flickr_-_The_U.S._Army_-_Soldiers_on_patrol_in_Korengal_Valley.jpg",
    },
  },
];

const battleScenes: Record<string, Scene> = {
  "battle-of-gettysburg": eraScenes[0].scene,
  "belleau-wood": {
    url: "https://upload.wikimedia.org/wikipedia/commons/9/95/Belleau_Wood_Hillside%2C_circa_1918_%288935802711%29.jpg",
    alt: "A hillside at Belleau Wood, about 1918.",
    credit: "U.S. Marine Corps Archives",
    license: "CC BY 2.0",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:Belleau_Wood_Hillside,_circa_1918_(8935802711).jpg",
  },
  "lost-battalion": eraScenes[2].scene,
  "battle-of-iwo-jima": eraScenes[3].scene,
  "chosin-reservoir": eraScenes[4].scene,
  "ia-drang": {
    url: "https://upload.wikimedia.org/wikipedia/commons/1/1b/Company_A%2C_229th_Helicopter_Assault_Battalion_UH-1Ds_take_off_from_Duc_Co.jpg",
    alt: "UH-1D helicopters of Company A, 229th Assault Helicopter Battalion, lifting off in Vietnam.",
    credit: "Spc. 6 Billy A. McBride, U.S. Army",
    license: "Public domain",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:Company_A,_229th_Helicopter_Assault_Battalion_UH-1Ds_take_off_from_Duc_Co.jpg",
  },
  "battle-of-kamdesh": eraScenes[6].scene,
  "mogadishu-1993": {
    url: "https://upload.wikimedia.org/wikipedia/commons/c/c4/Black_Hawk_Down_Super64_over_Mogadishu_coast.jpg",
    alt: "A U.S. Army Black Hawk, call sign Super 64, flying out over the Mogadishu coast on 3 October 1993.",
    credit: "U.S. Army photograph, via Wikimedia Commons",
    license: "Public domain",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:Black_Hawk_Down_Super64_over_Mogadishu_coast.jpg",
  },
  "second-battle-of-fallujah": {
    url: "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f7/4-14_Marines_in_Fallujah.jpg/1920px-4-14_Marines_in_Fallujah.jpg",
    alt: "A Marine M198 howitzer firing during the Second Battle of Fallujah.",
    credit: "Lance Cpl. Samantha L. Jones, U.S. Marine Corps",
    license: "Public domain",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:4-14_Marines_in_Fallujah.jpg",
  },
};

const eraSceneByName = new Map(eraScenes.map((item) => [item.era, item.scene]));

export function sceneForBattle(id: string, era: string) {
  return battleScenes[id] ?? eraSceneByName.get(era) ?? heroScene;
}

export function sceneForEra(era: string) {
  return eraSceneByName.get(era);
}
