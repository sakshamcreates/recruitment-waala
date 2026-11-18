"use client";

import { SlidersHorizontal } from "lucide-react";
import { useId, type FormEvent } from "react";
import { Button } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import {
  categories,
  categoryKeys,
  type Category,
} from "@/lib/catalogue/categories";
import { demoDate } from "@/lib/catalogue/fixtures";
import { formatDate } from "@/lib/format";
import {
  facet,
  facetKeys,
  readSearch,
  type SearchState,
} from "@/lib/catalogue/search";
import type { Opportunity } from "@/lib/catalogue/types";

const facetLabels = {
  state: "State",
  qualification: "Qualification",
  organisation: "Organisation",
  type: "Type",
  mode: "Work mode",
  duration: "Duration",
};

type FilterProps = {
  state: SearchState;
  items: readonly Opportunity[];
  category?: Category;
  onApply: (state: SearchState) => void;
  onClear: () => void;
};

function FilterForm({ state, items, category, onApply, onClear }: FilterProps) {
  const id = useId();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams();
    for (const [key, value] of new FormData(event.currentTarget)) {
      if (typeof value === "string") params.set(key, value);
    }
    params.set("q", state.q);
    params.set("sort", state.sort);
    onApply(readSearch(params));
  }

  return (
    <form className="filter-form" onSubmit={submit}>
      {!category && (
        <div className="filter-field">
          <label htmlFor={`${id}-category`}>Category</label>
          <select
            className="field"
            id={`${id}-category`}
            name="category"
            defaultValue={state.category}
          >
            <option value="">All categories</option>
            {categoryKeys.map((key) => (
              <option key={key} value={key}>
                {categories[key].label}
              </option>
            ))}
          </select>
        </div>
      )}
      {facetKeys.map((key) => {
        const values = [
          ...new Set(
            items
              .map((item) => facet(item, key))
              .filter((value): value is string => Boolean(value)),
          ),
        ].sort((a, b) => a.localeCompare(b, "en-IN"));
        const current = state[key];
        if (current && !values.includes(current)) values.push(current);
        if (!values.length) return null;
        return (
          <div className="filter-field" key={key}>
            <label htmlFor={`${id}-${key}`}>
              {key === "type" && category === "internships"
                ? "Compensation"
                : facetLabels[key]}
            </label>
            <select
              id={`${id}-${key}`}
              className="field"
              name={key}
              defaultValue={current}
            >
              <option value="">Any</option>
              {values.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
        );
      })}
      {(!category || items.some((item) => item.deadline) || state.deadline) && (
        <div className="filter-field">
          <label htmlFor={`${id}-deadline`}>Deadline</label>
          <select
            className="field"
            aria-describedby={`${id}-deadline-hint`}
            id={`${id}-deadline`}
            name="deadline"
            defaultValue={state.deadline}
          >
            <option value="">Any date</option>
            <option value="week">Within 7 days</option>
            <option value="month">Within 30 days</option>
          </select>
          <small className="filter-hint" id={`${id}-deadline-hint`}>
            From the demo date, {formatDate(demoDate, true)}.
          </small>
        </div>
      )}
      <div className="filter-buttons">
        <Button type="submit">Apply filters</Button>
        <Button type="button" variant="quiet" onClick={onClear}>
          Clear filters
        </Button>
      </div>
    </form>
  );
}

export function SearchFilters(props: FilterProps) {
  const key = JSON.stringify(props.state);
  return (
    <>
      <aside className="desktop-filters" aria-label="Filters">
        <h2>Filters</h2>
        <FilterForm key={key} {...props} />
      </aside>
      <Sheet
        className="mobile-filters"
        title="Filters"
        label="Open filters"
        trigger={
          <>
            <SlidersHorizontal size={16} aria-hidden="true" /> Filters
          </>
        }
      >
        {(close) => (
          <FilterForm
            key={key}
            {...props}
            onApply={(state) => {
              props.onApply(state);
              close();
            }}
            onClear={() => {
              props.onClear();
              close();
            }}
          />
        )}
      </Sheet>
    </>
  );
}
