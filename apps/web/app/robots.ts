import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  // Keep the preview crawlable so crawlers can read the noindex metadata.
  // Add sitemap and canonical origin once the official catalogue is published.
  return { rules: { userAgent: "*", allow: "/" } };
}
