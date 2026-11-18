import Link from "next/link";
import Form from "next/form";
import {
  ArrowRight,
  BriefcaseBusiness,
  ClipboardList,
  GraduationCap,
  Landmark,
  Search,
  Ticket,
} from "lucide-react";
import { Button, Input, PageContainer } from "@/components/ui/primitives";
import {
  categories,
  categoryKeys,
  primaryCategories,
} from "@/lib/catalogue/categories";
import { searchHref } from "@/lib/catalogue/search";

const categoryIcons = [
  Landmark,
  BriefcaseBusiness,
  GraduationCap,
  ClipboardList,
  Ticket,
];
const examples = ["Junior Engineer", "React", "Research intern"];

export function HeroSearch() {
  return (
    <Form
      action="/search"
      className="hero-search"
      role="search"
      aria-label="Search the catalogue"
    >
      <label className="hero-query">
        <Search size={22} aria-hidden="true" />
        <span className="sr-only">Keyword</span>
        <Input
          type="search"
          name="q"
          placeholder="Job title, exam or skill"
          maxLength={120}
        />
      </label>
      <div className="hero-category">
        <label htmlFor="hero-category" className="sr-only">
          Category
        </label>
        <select id="hero-category" name="category" className="field">
          <option value="">All categories</option>
          {categoryKeys.map((key) => (
            <option key={key} value={key}>
              {categories[key].label}
            </option>
          ))}
        </select>
      </div>
      <Button type="submit">
        Search <ArrowRight size={17} aria-hidden="true" />
      </Button>
    </Form>
  );
}

export function Hero() {
  return (
    <section className="hero">
      <PageContainer>
        <p className="eyebrow hero-tagline">
          <span />
          Every Opportunity. One Platform.
        </p>
        <h1>
          Your next opportunity <em>starts here.</em>
        </h1>
        <p className="hero-copy">
          Government jobs, private careers, internships and exam updates.
          Thoughtfully organised in one place.
        </p>
        <HeroSearch />
        <div className="example-searches">
          <span>Example searches</span>
          {examples.map((q) => (
            <Link href={searchHref("/search", { q })} key={q}>
              {q}
            </Link>
          ))}
        </div>
      </PageContainer>
    </section>
  );
}

export function CategoryNavigation() {
  return (
    <div className="category-band">
      <PageContainer>
        <nav
          className="category-navigation"
          aria-label="Opportunity categories"
        >
          {primaryCategories.map((key, index) => {
            const Icon = categoryIcons[index];
            return (
              <Link key={key} href={`/${key}`}>
                <Icon size={21} strokeWidth={1.7} aria-hidden="true" />
                <span>{categories[key].label}</span>
                <ArrowUpRightIcon />
              </Link>
            );
          })}
        </nav>
      </PageContainer>
    </div>
  );
}

function ArrowUpRightIcon() {
  return <ArrowRight className="category-arrow" size={15} aria-hidden="true" />;
}
