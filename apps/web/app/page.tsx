import { canonical } from "@/lib/metadata";
import { Hero, CategoryNavigation } from "@/components/home/hero";
import { HomeSections } from "@/components/home/sections";
import { upcomingDeadlineState } from "@/lib/catalogue/search";
import { catalogue, isDemo, liveSearch } from "@/lib/catalogue/repository";

export const metadata = canonical("/");

export default async function Home() {
  const [items, deadlines] = await Promise.all([
    catalogue.list(),
    isDemo ? undefined : liveSearch(upcomingDeadlineState, undefined, 3),
  ]);
  return (
    <>
      <Hero />
      <CategoryNavigation />
      <HomeSections items={items} demo={isDemo} deadlines={deadlines?.items} />
    </>
  );
}
