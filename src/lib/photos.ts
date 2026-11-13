import type { Photo } from "./records";

/**
 * Social cards may use a photograph only when the file already on the page
 * is public domain, CC0, or marked with no publication restrictions.
 * Creative Commons attribution licenses stay on the page, where the credit is visible.
 */
export function publicDomainPhotoUrl(photo: Photo | null): string | undefined {
  if (!photo) return undefined;
  const license = photo.license.toLowerCase();
  const unrestricted =
    license.includes("public domain") ||
    license.includes("cc0") ||
    license.includes("no known restrictions") ||
    /\bno restrictions\b/.test(license);
  return unrestricted ? photo.url : undefined;
}
