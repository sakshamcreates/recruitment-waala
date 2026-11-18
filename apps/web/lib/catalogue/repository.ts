import type { Category } from "./categories.ts";
import { fixtures } from "./fixtures.ts";
import type { Opportunity } from "./types.ts";

export interface CatalogueRepository {
  list(category?: Category): Promise<readonly Opportunity[]>;
  get(id: string): Promise<Opportunity | undefined>;
}

export const catalogue: CatalogueRepository = {
  async list(category) {
    return category
      ? fixtures.filter((item) => item.category === category)
      : fixtures;
  },
  async get(id) {
    return fixtures.find((item) => item.id === id);
  },
};
