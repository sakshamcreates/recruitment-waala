import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PreviewPage } from "@/components/layout/preview-page";
import { Card } from "@/components/ui/primitives";
import { DeadlineIndicator } from "@/components/catalogue/listings";
import { demoDate } from "@/lib/catalogue/fixtures";
import { upcomingDeadlines } from "@/lib/catalogue/search";
import { catalogue } from "@/lib/catalogue/repository";

export const metadata: Metadata = {
  title: "Dashboard preview",
  robots: { index: false, follow: false },
};

export default async function DashboardPage() {
  const [government, corporate] = await Promise.all([
    catalogue.list("government-jobs"),
    catalogue.list("corporate-jobs"),
  ]);
  const saved = [...government.slice(0, 1), ...corporate.slice(0, 1)];
  const deadlines = upcomingDeadlines(government, demoDate).slice(0, 2);
  return (
    <PreviewPage
      title="Career dashboard"
      description="A preview of how saved roles, applications and reminders could fit together."
      notice="The dashboard displays sample activity. Account sign-in, tracking and alert delivery are unavailable."
    >
      <div className="preview-grid">
        <Card className="preview-card">
          <h2>Saved jobs</h2>
          <ul className="preview-list">
            {saved.map((job) => (
              <li key={job.id}>
                <Link href={`/jobs/${job.id}`}>
                  {job.title}
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
                <small>{job.organisation}</small>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="preview-card">
          <h2>Application tracker</h2>
          <dl className="preview-list">
            <div>
              <dt>Junior Engineer (Civil)</dt>
              <dd>Example stage · Preparing documents</dd>
            </div>
            <div>
              <dt>Product Designer</dt>
              <dd>Example stage · Shortlisted to review</dd>
            </div>
          </dl>
        </Card>
        <Card className="preview-card">
          <h2>Job alerts</h2>
          <dl className="preview-list">
            <div>
              <dt>Graduate government jobs</dt>
              <dd>Sample weekly alert · Inactive</dd>
            </div>
            <div>
              <dt>Hybrid design roles</dt>
              <dd>Sample daily alert · Inactive</dd>
            </div>
          </dl>
        </Card>
        <Card className="preview-card">
          <h2>Upcoming deadlines</h2>
          <ul className="preview-list">
            {deadlines.map((job) => (
              <li key={job.id}>
                <Link href={`/jobs/${job.id}`}>
                  {job.title}
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
                <small>
                  <DeadlineIndicator value={job.deadline} />
                </small>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </PreviewPage>
  );
}
