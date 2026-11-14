function recipientParts(person) {
  const award = person.awards[0] ?? {};
  return [
    person.name,
    award.rank,
    award.conflict,
    award.actionYear ? String(award.actionYear) : "",
    award.actionPlace || "",
  ].filter(Boolean);
}

export function recipientDocumentTitle(person, people) {
  const same = people.filter((item) => item.name === person.name);
  if (same.length < 2) return person.name;
  const parts = recipientParts(person);
  for (let count = 2; count <= parts.length; count += 1) {
    const title = parts.slice(0, count).join(", ");
    const clashes = same.filter((item) => recipientParts(item).slice(0, count).join(", ") === title);
    if (clashes.length === 1) return title;
  }
  return `${parts.join(", ")}, ${person.id}`;
}

function battleParts(battle) {
  return [battle.title, battle.conflict, battle.dateLabel, battle.id].filter(Boolean);
}

export function battleDocumentTitle(battle, battles) {
  const same = battles.filter((item) => item.title === battle.title);
  if (same.length < 2) return battle.title;
  const parts = battleParts(battle);
  for (let count = 2; count <= parts.length; count += 1) {
    const title = parts.slice(0, count).join(", ");
    const clashes = same.filter((item) => battleParts(item).slice(0, count).join(", ") === title);
    if (clashes.length === 1) return title;
  }
  return parts.join(", ");
}

export function sourceLinkLabel(url, generalOrder) {
  const text = String(url || "");
  const ago = text.match(/AGO[_-](\d{4})-(\d+)/i);
  if (ago) return `Army General Order ${ago[1]}-${ago[2]}`;
  if (generalOrder && /armypubs\.army\.mil/i.test(text)) {
    const number = String(generalOrder).replace(/^AGO\s*/i, "");
    return `Army General Order ${number}`;
  }
  if (/army\.mil\/medalofhonor/i.test(text)) return "U.S. Army citation index";
  if (/dvidshub\.net/i.test(text)) return "DVIDS";
  try {
    return new URL(text).hostname.replace(/^www\./, "");
  } catch {
    return "Source";
  }
}
