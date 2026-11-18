import type { Metadata } from "next";

export function getSiteOrigin(): URL | undefined {
  const value = process.env.SITE_ORIGIN;
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (url.protocol === "https:" && !url.username && !url.password) {
      return new URL(url.origin);
    }
  } catch {
    // Phase 1 can run on a local address without a canonical base.
  }
  return undefined;
}

export function canonical(path: string): Pick<Metadata, "alternates"> {
  return getSiteOrigin() ? { alternates: { canonical: path } } : {};
}
