import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { Card } from "@/components/ui/primitives";
import { categories } from "@/lib/catalogue/categories";
import { formatDate } from "@/lib/format";
import type {
  CorporateJob,
  ExamNotice,
  GovernmentJob,
  Internship,
  Opportunity,
} from "@/lib/catalogue/types";

export function DeadlineIndicator({
  value,
  compact = false,
}: {
  value?: string;
  compact?: boolean;
}) {
  if (!value) return <span className="muted">Date unavailable</span>;
  return (
    <time dateTime={value} className="deadline-date">
      {formatDate(value, compact)}
    </time>
  );
}

export function GovernmentJobRow({ job }: { job: GovernmentJob }) {
  return (
    <article className="government-row">
      <div className="row-title">
        <p>{job.organisation}</p>
        <h3>
          <Link href={`/jobs/${job.id}`}>{job.title}</Link>
        </h3>
        <p className="reference">
          {job.reference} <span>·</span> {job.employment}
        </p>
      </div>
      <div className="row-meta">
        <span>Eligibility</span>
        <strong>{job.qualification}</strong>
      </div>
      <div className="row-meta">
        <span>Last date</span>
        <DeadlineIndicator value={job.deadline} />
      </div>
      <ArrowUpRight className="row-arrow" size={17} aria-hidden="true" />
    </article>
  );
}

export function CorporateJobCard({ job }: { job: CorporateJob }) {
  const initials = job.organisation
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("");
  return (
    <Card className="corporate-card">
      <article>
        <div className="company-line">
          <span className="initials" aria-hidden="true">
            {initials}
          </span>
          <span>{job.organisation}</span>
          <ArrowUpRight size={17} aria-hidden="true" />
        </div>
        <h3>
          <Link href={`/jobs/${job.id}`}>{job.title}</Link>
        </h3>
        <p>
          {[job.location, job.mode, job.experience].filter(Boolean).join(" · ")}
        </p>
        {job.salary && <p className="card-salary">{job.salary}</p>}
        <p className="skills">{job.skills.join(" · ")}</p>
      </article>
    </Card>
  );
}

export function InternshipRow({ job }: { job: Internship }) {
  return (
    <article className="simple-row internship-row">
      <div className="row-title">
        <p>{job.organisation}</p>
        <h3>
          <Link href={`/jobs/${job.id}`}>{job.title}</Link>
        </h3>
        <p>{[job.location, ...job.skills].filter(Boolean).join(" · ")}</p>
      </div>
      <div className="row-meta">
        <span>
          {job.duration} · {job.compensation}
        </span>
        {job.stipend && <strong>{job.stipend}</strong>}
      </div>
      <ArrowUpRight className="row-arrow" size={17} aria-hidden="true" />
    </article>
  );
}

export function ExamNoticeRow({ notice }: { notice: ExamNotice }) {
  return (
    <article className="simple-row exam-row">
      <div className="notice-date">
        <time dateTime={notice.publishedOn}>
          {formatDate(notice.publishedOn, true)}
        </time>
      </div>
      <div className="row-title">
        <p>
          {categories[notice.category].label} · {notice.organisation}
        </p>
        <h3>
          <Link href={`/jobs/${notice.id}`}>{notice.title}</Link>
        </h3>
        <p>
          {notice.stage}
          {notice.examOn && (
            <>
              {" "}
              · Exam{" "}
              <time dateTime={notice.examOn}>{formatDate(notice.examOn)}</time>
            </>
          )}
        </p>
      </div>
      <ArrowUpRight className="row-arrow" size={17} aria-hidden="true" />
    </article>
  );
}

export function OpportunityItem({ item }: { item: Opportunity }) {
  switch (item.category) {
    case "government-jobs":
      return <GovernmentJobRow job={item} />;
    case "corporate-jobs":
      return <CorporateJobCard job={item} />;
    case "internships":
      return <InternshipRow job={item} />;
    default:
      return <ExamNoticeRow notice={item} />;
  }
}
