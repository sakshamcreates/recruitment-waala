import { ArrowUpRight, Search } from "lucide-react";
import Link from "next/link";
import { PageContainer } from "@/components/ui/primitives";
import { MobileNavigation, NavigationLinks } from "./navigation";

function Wordmark() {
  return (
    <Link className="wordmark" href="/" aria-label="Recruitment Waala home">
      <span className="brand-mark" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      <span>
        Recruitment <strong>Waala</strong>
      </span>
    </Link>
  );
}

export function Navbar() {
  return (
    <header className="site-header">
      <PageContainer className="header-inner">
        <Wordmark />
        <NavigationLinks />
        <div className="header-actions">
          <Link
            className="header-search button button-secondary"
            href="/search"
            aria-label="Search opportunities"
          >
            <Search size={17} />
            <span>Search</span>
          </Link>
          <MobileNavigation />
        </div>
      </PageContainer>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="site-footer">
      <PageContainer>
        <div className="footer-main">
          <div>
            <Wordmark />
            <p>Every Opportunity. One Platform.</p>
          </div>
          <div className="footer-links">
            <Link href="/#sources">Source policy</Link>
            <Link href="/dashboard">
              Dashboard preview <ArrowUpRight size={14} />
            </Link>
            <Link href="/admin">
              Moderation preview <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>
        <div className="footer-note">
          Recruitment Waala · Illustrative catalogue
        </div>
      </PageContainer>
    </footer>
  );
}
