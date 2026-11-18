"use client";

import { ArrowLeft, ArrowRight, Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useRef, type FormEvent, type MouseEvent } from "react";
import { Button, Input } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/states";
import type { Category } from "@/lib/catalogue/categories";
import { demoDate } from "@/lib/catalogue/fixtures";
import {
  paginate,
  readSearch,
  searchCatalogue,
  searchHref,
  type SearchState,
} from "@/lib/catalogue/search";
import type { Opportunity } from "@/lib/catalogue/types";
import { OpportunityItem } from "./listings";
import { SearchFilters } from "./search-filters";

export function Pagination({
  page,
  totalPages,
  href,
  onPage,
}: {
  page: number;
  totalPages: number;
  href: (page: number) => string;
  onPage: (event: MouseEvent<HTMLAnchorElement>, page: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Results pagination">
      {page > 1 ? (
        <a
          className="button button-secondary"
          href={href(page - 1)}
          onClick={(event) => onPage(event, page - 1)}
        >
          <ArrowLeft size={16} aria-hidden="true" /> Previous
        </a>
      ) : (
        <span />
      )}
      <span>
        Page {page} of {totalPages}
      </span>
      {page < totalPages ? (
        <a
          className="button button-secondary"
          href={href(page + 1)}
          onClick={(event) => onPage(event, page + 1)}
        >
          Next <ArrowRight size={16} aria-hidden="true" />
        </a>
      ) : (
        <span />
      )}
    </nav>
  );
}

export function SearchResults({
  items,
  category,
  livePage,
}: {
  items: readonly Opportunity[];
  category?: Category;
  livePage?: {
    total: number;
    page: number;
    limit: number;
    facets: Record<string, string[]>;
  };
}) {
  const router = useRouter();
  const path = usePathname();
  const params = useSearchParams();
  const state = readSearch(params);
  if (category) state.category = "";
  const matches = livePage ? items : searchCatalogue(items, state, demoDate);
  const result = livePage
    ? {
        items,
        page: livePage.page,
        totalPages: Math.max(1, Math.ceil(livePage.total / livePage.limit)),
        start: (livePage.page - 1) * livePage.limit,
      }
    : paginate(matches, state.page);
  const total = livePage?.total ?? matches.length;
  const noun = livePage ? "opportunities" : "examples";
  const resultsHeading = useRef<HTMLHeadingElement>(null);
  const write = (next: Partial<SearchState>) => {
    const url = searchHref(path, next);
    if (url !== window.location.pathname + window.location.search)
      if (livePage) router.push(url);
      else window.history.pushState(null, "", url);
  };

  function apply(next: Partial<SearchState>) {
    write({ ...next, page: 1 });
    window.requestAnimationFrame(() => resultsHeading.current?.focus());
  }

  function submitKeyword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const query = data.get("q");
    if (typeof query === "string")
      apply({ ...state, q: query.trim().slice(0, 120) });
  }

  function goToPage(event: MouseEvent<HTMLAnchorElement>, page: number) {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    event.preventDefault();
    write({ ...state, page });
    resultsHeading.current?.focus();
  }

  const summary = total
    ? `Showing ${result.start + 1}–${result.start + result.items.length} of ${total} ${noun}`
    : `0 ${noun}`;

  return (
    <div className="browse-layout">
      <SearchFilters
        items={items}
        liveFacets={livePage?.facets}
        category={category}
        state={state}
        onApply={apply}
        onClear={() => apply({ q: state.q, sort: state.sort })}
      />
      <section className="browse-results" aria-labelledby="result-count">
        <form
          className="browse-search"
          onSubmit={submitKeyword}
          role="search"
          aria-label="Search within results"
        >
          <label>
            <Search size={20} aria-hidden="true" />
            <span className="sr-only">Search by keyword</span>
            <Input
              key={state.q}
              defaultValue={state.q}
              type="search"
              name="q"
              placeholder="Search by title, organisation or skill"
              maxLength={120}
            />
          </label>
          <Button type="submit">Search</Button>
        </form>
        <div className="results-toolbar">
          <h2
            id="result-count"
            ref={resultsHeading}
            tabIndex={-1}
            aria-live="polite"
          >
            {summary}
          </h2>
          <div className="sort-control">
            <label htmlFor="sort-results">Sort by</label>
            <select
              id="sort-results"
              className="field"
              value={state.sort}
              onChange={(event) => {
                write({
                  ...state,
                  sort: readSearch(
                    new URLSearchParams({ sort: event.target.value }),
                  ).sort,
                  page: 1,
                });
              }}
            >
              <option value="newest">Latest</option>
              <option value="deadline">Deadline</option>
              <option value="title">Title A–Z</option>
            </select>
          </div>
        </div>
        {result.items.length ? (
          <div
            className={
              category === "corporate-jobs"
                ? "corporate-grid browse-cards"
                : "ruled-list mixed-results"
            }
          >
            {result.items.map((item) => (
              <OpportunityItem item={item} key={item.id} />
            ))}
          </div>
        ) : (
          <EmptyState clearHref={path} />
        )}
        <Pagination
          page={result.page}
          totalPages={result.totalPages}
          href={(page) => searchHref(path, { ...state, page })}
          onPage={goToPage}
        />
      </section>
    </div>
  );
}
