import { Suspense } from "react";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { DemoNotice } from "@/components/ui/demo-notice";
import { PageContainer } from "@/components/ui/primitives";
import { LoadingState } from "@/components/ui/states";
import { categories, type Category } from "@/lib/catalogue/categories";
import { readSearch } from "@/lib/catalogue/search";
import { catalogue, isDemo, liveSearch } from "@/lib/catalogue/repository";
import { SearchResults } from "./search-results";

export type QueryParams = Record<string, string | string[] | undefined>;

export async function BrowsePage({
  category,
  query,
}: {
  category?: Category;
  query: Promise<QueryParams>;
}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(await query)) {
    if (typeof value === "string") params.set(key, value);
  }
  const livePage = isDemo
    ? undefined
    : await liveSearch(readSearch(params), category);
  const items = livePage?.items ?? (await catalogue.list(category));
  const title = category ? categories[category].label : "Search opportunities";
  return (
    <PageContainer className="internal-page">
      <Breadcrumbs items={[{ label: title }]} />
      <header className="page-heading">
        <h1>{title}</h1>
        <p>
          {category
            ? categories[category].description
            : "Search government jobs, corporate roles, internships and exam notices in one place."}
        </p>
      </header>
      {isDemo && <DemoNotice />}
      <Suspense fallback={<LoadingState />}>
        <SearchResults items={items} category={category} livePage={livePage} />
      </Suspense>
    </PageContainer>
  );
}
