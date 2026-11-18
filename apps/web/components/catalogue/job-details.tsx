import { ArrowRight, Clock3, Shield } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { DemoNotice } from "@/components/ui/demo-notice";
import { Card, PageContainer } from "@/components/ui/primitives";
import { categories } from "@/lib/catalogue/categories";
import type { Opportunity } from "@/lib/catalogue/types";
import { formatDate } from "@/lib/format";
import { DeadlineIndicator } from "./listings";

type Fact = readonly [string, ReactNode];

function detailsFor(item: Opportunity): Fact[] {
  switch (item.category) {
    case "government-jobs":
      return [
        ["Notification", item.reference],
        ["Qualification", item.qualification],
        ["Employment type", item.employment],
        ["Age requirement", item.age],
        ["Application fee", item.fee],
        ["Vacancies", item.vacancies],
        ["Salary", item.salary],
      ];
    case "corporate-jobs":
      return [
        ["Experience", item.experience],
        ["Work mode", item.mode],
        ["Employment type", item.employment],
        ["Salary", item.salary],
        ["Skills", item.skills.join(", ")],
      ];
    case "internships":
      return [
        ["Duration", item.duration],
        ["Compensation", item.compensation],
        ["Stipend", item.stipend],
        ["Skills", item.skills.join(", ")],
      ];
    default:
      return [
        ["Exam stage", item.stage],
        [
          "Exam date",
          item.examOn && (
            <time dateTime={item.examOn}>{formatDate(item.examOn)}</time>
          ),
        ],
      ];
  }
}

export function SourceAttribution({ item }: { item: Opportunity }) {
  const { organisation, provenance } = item;
  return (
    <Card className="detail-card source-attribution">
      <Shield size={22} aria-hidden="true" />
      <h2>Source attribution</h2>
      {provenance.kind === "illustrative" ? (
        <>
          <p>
            <strong>{organisation}</strong> is a fictional issuer used to
            demonstrate catalogue attribution.
          </p>
          <p>Official source unavailable in this preview.</p>
        </>
      ) : (
        <>
          <p>
            <strong>{organisation}</strong> · {provenance.source}
          </p>
          {provenance.verifiedOn && (
            <p>Reviewed on {formatDate(provenance.verifiedOn)}</p>
          )}
          {provenance.officialUrl && (
            <a
              className="text-link"
              href={provenance.officialUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Official notice
            </a>
          )}
        </>
      )}
    </Card>
  );
}

export function JobDetails({
  item,
  related,
}: {
  item: Opportunity;
  related: readonly Opportunity[];
}) {
  const exam = !["government-jobs", "corporate-jobs", "internships"].includes(
    item.category,
  );
  const demo = item.provenance.kind === "illustrative";
  const facts: Fact[] = [
    ["Organisation", item.organisation],
    ["Location", item.location],
    ...detailsFor(item),
  ];
  return (
    <PageContainer className="internal-page detail-page">
      <Breadcrumbs
        items={[
          { label: categories[item.category].label, href: `/${item.category}` },
          { label: item.title },
        ]}
      />
      <header className="page-heading">
        <p className="eyebrow">{categories[item.category].label}</p>
        <h1>{item.title}</h1>
        <p>
          {item.organisation}
          {item.location && ` · ${item.location}`}
        </p>
      </header>
      {demo ? (
        <DemoNotice>
          Illustrative record. This opportunity is unavailable for applications
          or downloads.
        </DemoNotice>
      ) : (
        item.status !== "published" && (
          <p className="demo-notice">
            This opportunity has been {item.status}.
          </p>
        )
      )}
      <div className="details-layout">
        <Card className="detail-card detail-dates">
          <Clock3 size={22} aria-hidden="true" />
          <h2>Important dates</h2>
          <dl className="date-facts">
            <div>
              <dt>{demo ? "Example notice date" : "Published"}</dt>
              <dd>
                <time dateTime={item.publishedOn}>
                  {formatDate(item.publishedOn)}
                </time>
              </dd>
            </div>
            {item.deadline && (
              <div>
                <dt>{demo ? "Example closing date" : "Closing date"}</dt>
                <dd>
                  <DeadlineIndicator value={item.deadline} />
                </dd>
              </div>
            )}
          </dl>
          {item.applyUrl ? (
            <a
              className="button button-primary"
              href={item.applyUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              {exam ? "Download" : "Apply"}
            </a>
          ) : (
            <p className="action-unavailable">
              {exam
                ? "Official notice unavailable"
                : "Applications unavailable"}
            </p>
          )}
        </Card>
        <div className="detail-body">
          <section className="detail-section">
            <h2>{exam ? "About the notice" : "Overview"}</h2>
            <p>{item.summary}</p>
          </section>
          <section className="detail-section">
            <h2>{exam ? "Notice details" : "Requirements and details"}</h2>
            <dl className="facts">
              {facts
                .filter(
                  ([, value]) =>
                    value != null && value !== false && value !== "",
                )
                .map(([name, value]) => (
                  <div key={name}>
                    <dt>{name}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
            </dl>
          </section>
        </div>
        <SourceAttribution item={item} />
      </div>
      {related.length > 0 && (
        <section className="detail-section related-section">
          <h2>{demo ? "Related examples" : "Related opportunities"}</h2>
          <ul>
            {related.map((job) => (
              <li key={job.id}>
                <Link href={`/jobs/${job.id}`}>
                  <span>
                    {job.title}
                    <small>{job.organisation}</small>
                  </span>
                  <ArrowRight size={17} aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </PageContainer>
  );
}
