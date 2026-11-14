/** Shared social-card URL rules. Imported by the site and by node:test. */

export const DEFAULT_SOCIAL_PATH = "/og.png";
export const DEFAULT_SOCIAL_WIDTH = 1200;
export const DEFAULT_SOCIAL_HEIGHT = 630;
export const DEFAULT_SOCIAL_ALT =
  "Valor Record. Every Medal of Honor recipient. Every story. U.S. soldiers wade from a Coast Guard landing craft toward Omaha Beach on D-Day, 6 June 1944.";

function originOf(origin) {
  return String(origin || "https://valorrecord.com").replace(/\/$/, "");
}

export function isWikimediaHotlink(url) {
  if (!url || typeof url !== "string") return false;
  try {
    const hostname = new URL(url.trim(), "https://valorrecord.com").hostname.toLowerCase();
    return (
      hostname === "wikimedia.org" ||
      hostname.endsWith(".wikimedia.org") ||
      hostname === "wikipedia.org" ||
      hostname.endsWith(".wikipedia.org")
    );
  } catch {
    return false;
  }
}

/** A file this site serves: a site-root path, or an absolute URL on our origin. */
export function isSelfHostedAsset(url, origin) {
  if (!url || typeof url !== "string") return false;
  const value = url.trim();
  if (!value || value.startsWith("//") || isWikimediaHotlink(value)) return false;
  if (/^https?:\/\//i.test(value)) {
    try {
      return new URL(value).origin === originOf(origin);
    } catch {
      return false;
    }
  }
  return !value.includes("://");
}

export function usesDefaultSocialImage(image, origin) {
  return !isSelfHostedAsset(image, origin);
}

export function resolveSocialImage(image, origin) {
  const base = originOf(origin);
  if (usesDefaultSocialImage(image, origin)) return `${base}${DEFAULT_SOCIAL_PATH}`;
  const value = image.trim();
  if (/^https?:\/\//i.test(value)) return value;
  return `${base}${value.startsWith("/") ? value : `/${value}`}`;
}
