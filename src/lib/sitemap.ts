/** Sitemap protocol limit for URLs in one file. */
export const SITEMAP_URL_LIMIT = 50_000;

/**
 * The not-found page is a host error document, not an archive URL.
 * `/404` is the canonical form. `/404.html` is the file Render serves.
 */
const NOT_FOUND_PATHS = new Set(["/404", "/404.html", "/404/"]);

export function isNotFoundLocation(value: string): boolean {
  let path = value.split("?")[0].split("#")[0];
  if (path.includes("://")) {
    try {
      path = new URL(path).pathname;
    } catch {
      return false;
    }
  }
  if (!path.startsWith("/")) path = `/${path}`;
  return NOT_FOUND_PATHS.has(path);
}

const URLSET_NS = "http://www.sitemaps.org/schemas/sitemap/0.9";

export interface SitemapFile {
  name: string;
  body: string;
}

function escapeXml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function urlset(urls: string[], lastmod: string): string {
  const entries = urls
    .map(
      (url) =>
        `  <url>\n    <loc>${escapeXml(url)}</loc>\n    <lastmod>${escapeXml(lastmod)}</lastmod>\n  </url>`,
    )
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="${URLSET_NS}">\n${entries}\n</urlset>\n`;
}

function sitemapIndex(childNames: string[], origin: string, lastmod: string): string {
  const entries = childNames
    .map(
      (name) =>
        `  <sitemap>\n    <loc>${escapeXml(`${origin}/${name}`)}</loc>\n    <lastmod>${escapeXml(lastmod)}</lastmod>\n  </sitemap>`,
    )
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="${URLSET_NS}">\n${entries}\n</sitemapindex>\n`;
}

/**
 * One `sitemap.xml` urlset while the archive is under the protocol limit.
 * Above that, `sitemap.xml` is an index and each child is `sitemap-N.xml`.
 */
export function renderSitemaps(
  urls: string[],
  lastmod: string,
  origin: string,
  limit = SITEMAP_URL_LIMIT,
): SitemapFile[] {
  if (urls.length <= limit) {
    return [{ name: "sitemap.xml", body: urlset(urls, lastmod) }];
  }
  const children: SitemapFile[] = [];
  for (let index = 0; index < urls.length; index += limit) {
    const chunk = urls.slice(index, index + limit);
    children.push({
      name: `sitemap-${children.length + 1}.xml`,
      body: urlset(chunk, lastmod),
    });
  }
  return [
    {
      name: "sitemap.xml",
      body: sitemapIndex(
        children.map((child) => child.name),
        origin,
        lastmod,
      ),
    },
    ...children,
  ];
}
