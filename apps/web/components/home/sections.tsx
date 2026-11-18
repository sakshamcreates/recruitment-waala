import Link from "next/link";
import { ArrowRight, CalendarDays, Shield } from "lucide-react";
import {
  CorporateJobCard,
  DeadlineIndicator,
  ExamNoticeRow,
  GovernmentJobRow,
  InternshipRow,
} from "@/components/catalogue/listings";
import { demoDate } from "@/lib/catalogue/fixtures";
import {
  readSearch,
  searchCatalogue,
  searchHref,
  upcomingDeadlines,
  upcomingDeadlineState,
} from "@/lib/catalogue/search";
import type { ExamNotice, Opportunity } from "@/lib/catalogue/types";
import { DemoNotice } from "@/components/ui/demo-notice";
import { Card, PageContainer } from "@/components/ui/primitives";

function SectionHeading({
  id,
  title,
  href,
  action,
}: {
  id: string;
  title: string;
  href: string;
  action: string;
}) {
  return (
    <div className="section-heading">
      <h2 id={id}>{title}</h2>
      <Link className="text-link" href={href}>
        {action}
        <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </div>
  );
}

function DeadlineList({ items }: { items: readonly Opportunity[] }) {
  const upcoming = upcomingDeadlines(items, demoDate).slice(0, 3);
  return (
    <aside className="deadline-panel" aria-labelledby="deadlines-title">
      <div className="deadline-heading">
        <CalendarDays size={20} aria-hidden="true" />
        <h2 id="deadlines-title">Upcoming deadlines</h2>
      </div>
      <p>Dates from the illustrative catalogue.</p>
      <ul>
        {upcoming.map((item) => (
          <li key={item.id}>
            <span className="date-tile">
              <DeadlineIndicator value={item.deadline} compact />
            </span>
            <div>
              <Link href={`/jobs/${item.id}`}>{item.title}</Link>
              <span>{item.organisation}</span>
            </div>
          </li>
        ))}
      </ul>
      <Link
        href={searchHref("/search", upcomingDeadlineState)}
        className="text-link"
      >
        Browse deadlines <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </aside>
  );
}

export function HomeSections({ items }: { items: readonly Opportunity[] }) {
  const newest = searchCatalogue(items, readSearch(), demoDate);
  const government = newest.filter(
    (item) => item.category === "government-jobs",
  );
  const corporate = newest.filter((item) => item.category === "corporate-jobs");
  const internships = newest.filter((item) => item.category === "internships");
  const exams = newest.filter(
    (item): item is ExamNotice =>
      item.category === "results" || item.category === "admit-cards",
  );
  return (
    <PageContainer className="home-content">
      <DemoNotice />
      <div className="home-lead">
        <section aria-labelledby="government-heading">
          <SectionHeading
            id="government-heading"
            title="Latest government jobs"
            href="/government-jobs"
            action="All government jobs"
          />
          <div className="ruled-list">
            {government.slice(0, 3).map((job) => (
              <GovernmentJobRow key={job.id} job={job} />
            ))}
          </div>
        </section>
        <DeadlineList items={items} />
      </div>
      <section className="home-section" aria-labelledby="corporate-heading">
        <SectionHeading
          id="corporate-heading"
          title="Corporate careers"
          href="/corporate-jobs"
          action="All corporate jobs"
        />
        <div className="corporate-grid">
          {corporate.map((job) => (
            <CorporateJobCard key={job.id} job={job} />
          ))}
        </div>
      </section>
      <div className="home-duo home-section">
        <section aria-labelledby="internships-heading">
          <SectionHeading
            id="internships-heading"
            title="Internships"
            href="/internships"
            action="All internships"
          />
          <div className="ruled-list">
            {internships.map((job) => (
              <InternshipRow key={job.id} job={job} />
            ))}
          </div>
        </section>
        <section aria-labelledby="exams-heading">
          <SectionHeading
            id="exams-heading"
            title="Exam updates"
            href="/results"
            action="All results"
          />
          <div className="ruled-list">
            {exams.map((notice) => (
              <ExamNoticeRow key={notice.id} notice={notice} />
            ))}
          </div>
          <nav className="exam-links" aria-label="More exam updates">
            <Link href="/admit-cards">Admit cards</Link>
            <Link href="/answer-keys">Answer keys</Link>
            <Link href="/syllabus">Syllabus</Link>
          </nav>
        </section>
      </div>
      <Card className="source-panel" id="sources">
        <Shield size={26} strokeWidth={1.6} aria-hidden="true" />
        <div>
          <h2>Know where an opportunity comes from.</h2>
          <p>
            Published opportunities will identify the issuing organisation and
            link to its official notice. This preview uses fictional issuers and
            example dates, so it has no official application or download links.
          </p>
        </div>
      </Card>
    </PageContainer>
  );
}
