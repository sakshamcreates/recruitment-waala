import { connection } from "next/server";
import { apiCategories, mapOpportunity, mapPage } from "./api-adapter";
import { categoryKeys, type Category } from "./categories";
import { demoCatalogue } from "./demo-repository";
import { pageSize, searchHref, type SearchState } from "./search";
import type { Opportunity } from "./types";

export const isDemo =
  process.env.CATALOGUE_MODE === "demo" &&
  process.env.NODE_ENV !== "production";

export interface CatalogueRepository {
  list(category?: Category): Promise<readonly Opportunity[]>;
  get(id: string): Promise<Opportunity | undefined>;
}

async function request(path: string, allowMissing = false): Promise<unknown> {
  await connection();
  const origin = process.env.CATALOGUE_API_ORIGIN;
  if (!origin) throw new Error("Catalogue API is not configured.");
  const response = await fetch(new URL(`/api/v1${path}`, origin), {
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
    redirect: "error",
  });
  if (allowMissing && response.status === 404) return undefined;
  if (!response.ok) throw new Error("Catalogue API unavailable.");
  return response.json();
}

export async function liveSearch(
  state: Partial<SearchState>,
  category?: Category,
  limit = pageSize,
) {
  const selected = category || state.category;
  const query = new URL(
    searchHref("/opportunities", state),
    "http://localhost",
  );
  if (selected) query.searchParams.set("category", apiCategories[selected]);
  query.searchParams.set("limit", String(limit));
  return mapPage(await request(query.pathname + query.search));
}

export const catalogue: CatalogueRepository = isDemo
  ? demoCatalogue
  : {
      async list(category) {
        if (category) return (await liveSearch({}, category, 3)).items;
        return (
          await Promise.all(categoryKeys.map((key) => liveSearch({}, key, 3)))
        ).flatMap((page) => page.items);
      },
      async get(id) {
        if (!/^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(id))
          return undefined;
        const raw = await request(`/opportunities/${id}`, true);
        return raw === undefined ? undefined : mapOpportunity(raw);
      },
    };
