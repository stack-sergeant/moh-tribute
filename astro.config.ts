import { defineConfig } from "astro/config";
import { sitemapIntegration } from "./src/integrations/sitemap";
import { site } from "./src/site";

export default defineConfig({
  site: site.origin,
  output: "static",
  build: {
    format: "directory",
  },
  redirects: {
    "/recipients/richard-1-bong": "/recipients/richard-i-bong",
    "/recipients/daniel-1-holcomb": "/recipients/daniel-i-holcomb",
    "/recipients/james-1-mestrovitch": "/recipients/james-i-mestrovitch",
    "/recipients/samuel-1-parker": "/recipients/samuel-i-parker",
    "/recipients/harvey-c-ir-barnum": "/recipients/harvey-c-barnum-jr",
  },
  integrations: [sitemapIntegration()],
});
