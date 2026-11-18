import { canonical } from "@/lib/metadata";
import type { Metadata } from "next";
import { BrowsePage } from "@/components/catalogue/browse-page";

export const metadata: Metadata = {
  ...canonical("/search"),
  title: "Search opportunities",
  description:
    "Filter, sort and explore the illustrative Recruitment Waala catalogue.",
};

export default function SearchPage() {
  return <BrowsePage />;
}
