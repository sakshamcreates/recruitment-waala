import { canonical } from "@/lib/metadata";
import { Hero, CategoryNavigation } from "@/components/home/hero";
import { HomeSections } from "@/components/home/sections";
import { catalogue } from "@/lib/catalogue/repository";

export const metadata = canonical("/");

export default async function Home() {
  const items = await catalogue.list();
  return (
    <>
      <Hero />
      <CategoryNavigation />
      <HomeSections items={items} />
    </>
  );
}
