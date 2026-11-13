import { site } from "../site";

/**
 * Render serves each directory index at both `/about` and `/about/`.
 * Links on the site omit the trailing slash, so canonical URLs do too.
 * The homepage is the one exception: its path is `/`.
 */
export function canonicalPath(pathname: string): string {
  let path = pathname.split("?")[0].split("#")[0];
  if (path === "index.html" || path === "/index.html") path = "/";
  else if (path.endsWith("/index.html")) path = path.slice(0, -"index.html".length);
  else if (path.endsWith(".html")) path = path.slice(0, -".html".length);
  if (!path.startsWith("/")) path = `/${path}`;
  if (path.length > 1 && path.endsWith("/")) path = path.slice(0, -1);
  return path || "/";
}

export function pageUrl(pathname: string): string {
  return `${site.origin}${canonicalPath(pathname)}`;
}

export function absoluteAssetUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  return `${site.origin}${url.startsWith("/") ? url : `/${url}`}`;
}
