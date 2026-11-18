import Link from "next/link";
import { Info, Search } from "lucide-react";
import { buttonStyle, PageContainer } from "./primitives";

export function EmptyState({ clearHref }: { clearHref: string }) {
  return (
    <div className="state-box">
      <Search size={24} aria-hidden="true" />
      <h2>No matching opportunities</h2>
      <p>Try a broader keyword or remove a filter.</p>
      <Link className={buttonStyle.secondary} href={clearHref}>
        Clear search and filters
      </Link>
    </div>
  );
}

export function LoadingState() {
  return (
    <PageContainer className="loading-state" role="status">
      <p>Loading opportunities…</p>
      <div aria-hidden="true" />
      <div aria-hidden="true" />
      <div aria-hidden="true" />
    </PageContainer>
  );
}

export function ErrorState({ retry }: { retry: () => void }) {
  return (
    <div className="state-box">
      <Info className="error-color" size={24} aria-hidden="true" />
      <h1>We couldn’t load this page</h1>
      <p>Try again or return to the catalogue.</p>
      <button className={buttonStyle.primary} type="button" onClick={retry}>
        Try again
      </button>
      <Link className="text-link" href="/">
        Return home
      </Link>
    </div>
  );
}
