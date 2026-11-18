import { isCategory, type Category } from "./categories.ts";
import type { Opportunity } from "./types.ts";

export const pageSize = 5;
export const facetKeys = [
  "state",
  "qualification",
  "experience",
  "organisation",
  "type",
  "mode",
  "duration",
] as const;
type TextField = (typeof facetKeys)[number];
export type SearchState = Record<TextField, string> & {
  q: string;
  category: Category | "";
  deadline: "" | "week" | "month";
  sort: "newest" | "deadline" | "title";
  page: number;
};

export function readSearch(
  params: Pick<URLSearchParams, "get"> = new URLSearchParams(),
): SearchState {
  const get = (key: string) => (params.get(key) ?? "").trim().slice(0, 120);
  const category = get("category");
  const deadline = get("deadline");
  const sort = get("sort");
  const page = get("page");
  return {
    q: get("q"),
    category: isCategory(category) ? category : "",
    state: get("state"),
    qualification: get("qualification"),
    experience: get("experience"),
    organisation: get("organisation"),
    type: get("type"),
    mode: get("mode"),
    duration: get("duration"),
    deadline: deadline === "week" || deadline === "month" ? deadline : "",
    sort: sort === "deadline" || sort === "title" ? sort : "newest",
    page: /^\d{1,5}$/.test(page) ? Math.max(1, Number(page)) : 1,
  };
}

export function searchHref(path: string, state: Partial<SearchState>): string {
  const params = new URLSearchParams();
  for (const [name, value] of Object.entries(state)) {
    if (
      value &&
      !(name === "page" && value === 1) &&
      !(name === "sort" && value === "newest")
    ) {
      params.set(name, String(value));
    }
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function facet(item: Opportunity, key: TextField): string | undefined {
  switch (key) {
    case "experience":
      return "experience" in item ? item.experience : undefined;
    case "qualification":
      return "qualification" in item ? item.qualification : undefined;
    case "type":
      return "employment" in item
        ? item.employment
        : "compensation" in item
          ? item.compensation
          : undefined;
    case "mode":
      return "mode" in item ? item.mode : undefined;
    case "duration":
      return "duration" in item ? item.duration : undefined;
    default:
      return item[key];
  }
}

export function searchCatalogue(
  items: readonly Opportunity[],
  state: SearchState,
  referenceDate: string,
) {
  const tokens = state.q
    .toLocaleLowerCase("en-IN")
    .split(/\s+/)
    .filter(Boolean);
  const endDate = new Date(referenceDate);
  endDate.setUTCDate(
    endDate.getUTCDate() + (state.deadline === "week" ? 7 : 30),
  );
  const deadlineLimit = endDate.toISOString().slice(0, 10);
  const matches = items.filter((item) => {
    if (state.category && item.category !== state.category) return false;
    if (facetKeys.some((key) => state[key] && facet(item, key) !== state[key]))
      return false;
    if (
      state.deadline &&
      (!item.deadline ||
        item.deadline < referenceDate ||
        item.deadline > deadlineLimit)
    )
      return false;
    const haystack = [
      item.title,
      item.organisation,
      item.location,
      item.state,
      item.summary,
      "reference" in item ? item.reference : undefined,
      "skills" in item ? item.skills.join(" ") : undefined,
      "qualification" in item ? item.qualification : undefined,
      "stage" in item ? item.stage : undefined,
    ]
      .join(" ")
      .toLocaleLowerCase("en-IN");
    return tokens.every((token) => haystack.includes(token));
  });
  return matches.sort((a, b) => {
    if (state.sort === "title")
      return (
        a.title.localeCompare(b.title, "en-IN") || a.id.localeCompare(b.id)
      );
    if (state.sort === "deadline") {
      const difference = (a.deadline ?? "9999").localeCompare(
        b.deadline ?? "9999",
      );
      if (difference) return difference;
    }
    return (
      b.publishedOn.localeCompare(a.publishedOn) || a.id.localeCompare(b.id)
    );
  });
}

export function paginate<T>(items: readonly T[], requestedPage: number) {
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const page = Math.min(Math.max(1, requestedPage), totalPages);
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    page,
    totalPages,
    start,
  };
}

export const upcomingDeadlineState = {
  sort: "deadline",
  deadline: "month",
} as const;

export function upcomingDeadlines(
  items: readonly Opportunity[],
  referenceDate: string,
) {
  return searchCatalogue(
    items,
    { ...readSearch(), ...upcomingDeadlineState },
    referenceDate,
  );
}
