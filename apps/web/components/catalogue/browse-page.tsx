import { Suspense } from "react";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { DemoNotice } from "@/components/ui/demo-notice";
import { PageContainer } from "@/components/ui/primitives";
import { LoadingState } from "@/components/ui/states";
import { categories, type Category } from "@/lib/catalogue/categories";
import { catalogue } from "@/lib/catalogue/repository";
import { SearchResults } from "./search-results";

export async function BrowsePage({ category }: { category?: Category }) {
  const items = await catalogue.list(category);
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
      <DemoNotice />
      <Suspense fallback={<LoadingState />}>
        <SearchResults items={items} category={category} />
      </Suspense>
    </PageContainer>
  );
}
