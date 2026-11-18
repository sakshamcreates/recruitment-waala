"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, Menu, Search } from "lucide-react";
import {
  categories,
  primaryCategories,
  type Category,
} from "@/lib/catalogue/categories";
import { Sheet } from "@/components/ui/sheet";

function CategoryLinks({
  close,
  items = primaryCategories,
}: {
  close?: () => void;
  items?: readonly Category[];
}) {
  const path = usePathname();
  return items.map((key) => {
    const href = `/${key}`;
    return (
      <Link
        key={key}
        href={href}
        onClick={close}
        aria-current={path === href ? "page" : undefined}
      >
        {categories[key].label}
      </Link>
    );
  });
}

export function NavigationLinks() {
  return (
    <nav className="desktop-nav" aria-label="Primary">
      <CategoryLinks />
    </nav>
  );
}

export function MobileNavigation() {
  return (
    <Sheet
      className="mobile-navigation"
      label="Open navigation"
      title="Explore Recruitment Waala"
      trigger={<Menu size={20} />}
    >
      {(close) => (
        <nav className="mobile-links" aria-label="Mobile">
          <Link href="/search" onClick={close}>
            <span>Search opportunities</span>
            <Search size={16} />
          </Link>
          <CategoryLinks
            items={[...primaryCategories, "answer-keys", "syllabus"]}
            close={close}
          />
          <Link href="/dashboard" onClick={close}>
            Dashboard preview <ArrowUpRight size={16} />
          </Link>
          <Link href="/admin" onClick={close}>
            Moderation preview <ArrowUpRight size={16} />
          </Link>
        </nav>
      )}
    </Sheet>
  );
}
