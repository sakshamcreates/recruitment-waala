import { canonical } from "@/lib/metadata";
import type { Metadata } from "next";
import {
  BrowsePage,
  type QueryParams,
} from "@/components/catalogue/browse-page";

export const metadata: Metadata = {
  ...canonical("/search"),
  title: "Search opportunities",
  robots: { index: false, follow: true },
  description: "Filter, sort and explore the Recruitment Waala catalogue.",
};

export default function SearchPage({
  searchParams,
}: {
  searchParams: Promise<QueryParams>;
}) {
  return <BrowsePage query={searchParams} />;
}
