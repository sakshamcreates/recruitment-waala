import { canonical } from "@/lib/metadata";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BrowsePage } from "@/components/catalogue/browse-page";
import {
  categories,
  categoryKeys,
  isCategory,
} from "@/lib/catalogue/categories";

type Props = { params: Promise<{ category: string }> };
export const dynamicParams = false;

export function generateStaticParams() {
  return categoryKeys.map((category) => ({ category }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  if (!isCategory(category)) notFound();
  return {
    ...canonical(`/${category}`),
    title: categories[category].label,
    description: categories[category].description,
  };
}

export default async function CategoryPage({ params }: Props) {
  const { category } = await params;
  if (!isCategory(category)) notFound();
  return <BrowsePage category={category} />;
}
