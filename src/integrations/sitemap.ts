import { execFileSync } from "node:child_process";
import { access, readFile, readdir, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { AstroIntegration } from "astro";
import { isNotFoundLocation, renderSitemaps } from "../lib/sitemap";
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
        const urls = [
          ...new Set(
            pages
              .filter((page) => !isNotFoundLocation(page.pathname))
              .map((page) => pageUrl(page.pathname))
              .filter((url) => !isNotFoundLocation(url)),
          ),
        ].sort((a, b) => {
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
        const notFoundLoc = new RegExp(
          `<loc>${site.origin.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/404(?:\\.html)?</loc>`,
        );
        const leaked = files.filter((file) => notFoundLoc.test(file.body));
        if (leaked.length > 0) {
          throw new Error(
            `Sitemap still lists the not-found page: ${leaked.map((file) => file.name).join(", ")}`,
          );
        }
        await Promise.all(
          files.map((file) => writeFile(path.join(outDir, file.name), file.body, "utf8")),
        );
        await ensureRootNotFoundPage(outDir);
        logger.info(
          `Wrote ${files.map((file) => file.name).join(", ")} with ${urls.length} page URLs (lastmod ${lastmod}).`,
        );
      },
    },
  };
}

async function exists(file: string): Promise<boolean> {
  try {
    await access(file);
    return true;
  } catch {
    return false;
  }
}

/**
 * Render serves a root `404.html` with status 404 for unknown paths.
 * A `404/index.html` from directory output is an ordinary page and returns 200.
 */
async function ensureRootNotFoundPage(outDir: string): Promise<void> {
  const rootPage = path.join(outDir, "404.html");
  const nestedDir = path.join(outDir, "404");
  const nestedPage = path.join(nestedDir, "index.html");
  if ((await exists(nestedPage)) && !(await exists(rootPage))) {
    await rename(nestedPage, rootPage);
  } else if (await exists(nestedPage)) {
    await rm(nestedPage);
  }
  if (await exists(nestedDir)) {
    const leftover = await readdir(nestedDir);
    if (leftover.length === 0) await rm(nestedDir, { recursive: true });
  }
  if (!(await exists(rootPage))) {
    throw new Error(
      "Build did not emit 404.html. Render serves that root file with status 404 for unknown paths.",
    );
  }
  const html = await readFile(rootPage, "utf8");
  if (!html.includes('name="robots" content="noindex"')) {
    throw new Error('404.html is missing <meta name="robots" content="noindex">.');
  }
}
