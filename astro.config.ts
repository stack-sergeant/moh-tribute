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
    "/recipients/pitsenbarger-william-h": "/recipients/william-h-pitsenbarger",
    "/recipients/james-mclntosh": "/recipients/james-mcintosh",
    "/recipients/fred-henry-mcgulre": "/recipients/fred-henry-mcguire",
    "/recipients/patrick-mcgulre": "/recipients/patrick-mcguire",
    "/recipients/thomas-b-mcgulre-jr": "/recipients/thomas-b-mcguire-jr",
    "/recipients/vernon-mcgarlty": "/recipients/vernon-mcgarity",
    "/recipients/patrick-regan-2": "/recipients/patrick-regan-1918",
  },
  integrations: [sitemapIntegration()],
});
