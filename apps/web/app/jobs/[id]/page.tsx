import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { JobDetails } from "@/components/catalogue/job-details";
import { catalogue } from "@/lib/catalogue/repository";

type Props = { params: Promise<{ id: string }> };
export const dynamicParams = false;

export async function generateStaticParams() {
  return (await catalogue.list()).map(({ id }) => ({ id }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const item = await catalogue.get((await params).id);
  if (!item) notFound();
  return {
    title: `${item.title} (illustrative)`,
    description: item.summary,
    robots: { index: false, follow: true },
  };
}

export default async function DetailPage({ params }: Props) {
  const item = await catalogue.get((await params).id);
  if (!item) notFound();
  const related = (await catalogue.list(item.category))
    .filter(({ id }) => id !== item.id)
    .sort(
      (a, b) =>
        Number(b.organisation === item.organisation) -
        Number(a.organisation === item.organisation),
    )
    .slice(0, 3);
  return <JobDetails item={item} related={related} />;
}
