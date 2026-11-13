import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { AstroIntegration } from "astro";
import { renderSitemaps } from "../lib/sitemap";
import { pageUrl } from "../lib/urls";
import { site } from "../site";

function commitDay(): string {
  try {
    const iso = execFileSync("git", ["log", "-1", "--format=%cI"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    const day = iso.slice(0, 10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(day)) return day;
  } catch {
    // A build without a git checkout still needs a lastmod.
  }
  return new Date().toISOString().slice(0, 10);
}

export function sitemapIntegration(): AstroIntegration {
  return {
    name: "valor-sitemap",
    hooks: {
      "astro:build:done": async ({ dir, pages, logger }) => {
        const urls = [...new Set(pages.map((page) => pageUrl(page.pathname)))].sort((a, b) => {
          if (a === `${site.origin}/`) return -1;
          if (b === `${site.origin}/`) return 1;
          return a.localeCompare(b);
        });
        if (urls.length === 0) {
          throw new Error("Sitemap build found no pages.");
        }
        for (const url of urls) {
          let parsed: URL;
          try {
            parsed = new URL(url);
          } catch {
            throw new Error(`Sitemap URL is not absolute: ${url}`);
          }
          if (parsed.origin !== site.origin) {
            throw new Error(`Sitemap URL is not on ${site.origin}: ${url}`);
          }
          if (parsed.pathname !== "/" && parsed.pathname.endsWith("/")) {
            throw new Error(`Sitemap URL has a trailing slash: ${url}`);
          }
        }
        const lastmod = commitDay();
        const files = renderSitemaps(urls, lastmod, site.origin);
        const outDir = fileURLToPath(dir);
        await Promise.all(
          files.map((file) => writeFile(path.join(outDir, file.name), file.body, "utf8")),
        );
        logger.info(
          `Wrote ${files.map((file) => file.name).join(", ")} with ${urls.length} page URLs (lastmod ${lastmod}).`,
        );
      },
    },
  };
}
