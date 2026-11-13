import { defineConfig } from "astro/config";
import { sitemapIntegration } from "./src/integrations/sitemap";
import { site } from "./src/site";

export default defineConfig({
  site: site.origin,
  output: "static",
  build: {
    format: "directory",
  },
  integrations: [sitemapIntegration()],
});
