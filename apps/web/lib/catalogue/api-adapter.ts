import type { Category } from "./categories.ts";
import type { Opportunity } from "./types.ts";

export const apiCategories = {
  "government-jobs": "government_job",
  "corporate-jobs": "corporate_job",
  internships: "internship",
  results: "result",
  "admit-cards": "admit_card",
  "answer-keys": "answer_key",
  syllabus: "syllabus",
} satisfies Record<Category, string>;

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error("Invalid catalogue response");
  return value as Record<string, unknown>;
}

const optional = (value: unknown) =>
  typeof value === "string" ? value : undefined;
function required(value: unknown) {
  if (typeof value !== "string" || !value)
    throw new Error("Invalid catalogue response");
  return value;
}

function officialUrl(value: unknown) {
  if (typeof value !== "string") return undefined;
  try {
    const url = new URL(value);
    if (url.protocol === "https:" && !url.username && !url.password)
      return url.href;
  } catch {
    return undefined;
  }
}

const localDate = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Kolkata",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
function date(value: unknown) {
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value)))
    return undefined;
  return localDate.format(new Date(value));
}

export function mapOpportunity(raw: unknown): Opportunity {
  const row = record(raw);
  const fields = record(row.details);
  const category = (Object.keys(apiCategories) as Category[]).find(
    (key) => apiCategories[key] === fields.category,
  );
  const source = record(row.provenance);
  const status = row.status;
  if (
    !category ||
    (status !== "published" && status !== "expired" && status !== "withdrawn")
  )
    throw new Error("Unsupported catalogue record");
  const publishedOn = date(row.published_at);
  if (!publishedOn) throw new Error("Invalid publication date");
  const provenance = {
    kind: "official" as const,
    source: required(source.source),
    officialUrl: officialUrl(source.official_url),
    verifiedOn: date(source.verified_at),
  };
  const base: Omit<Opportunity, "category"> = {
    id: required(row.id),
    title: required(row.title),
    organisation: required(row.organisation),
    summary: optional(row.description) ?? "",
    location: optional(row.location),
    state: optional(fields.state),
    publishedOn,
    deadline: date(row.deadline),
    status,
    applyUrl: status === "published" ? officialUrl(row.apply_url) : undefined,
    provenance,
  };
  const skills = Array.isArray(fields.skills)
    ? fields.skills.filter((item): item is string => typeof item === "string")
    : [];
  switch (category) {
    case "government-jobs":
      return {
        ...base,
        category,
        reference: optional(fields.reference),
        qualification: optional(fields.qualification),
        employment: optional(fields.employment),
        age: optional(fields.age),
        fee: optional(fields.fee),
        vacancies:
          typeof fields.vacancies === "number" ? fields.vacancies : undefined,
        salary: optional(fields.salary),
      };
    case "corporate-jobs":
      return {
        ...base,
        category,
        experience: optional(fields.experience),
        mode: optional(fields.mode),
        employment: optional(fields.employment),
        salary: optional(fields.salary),
        skills,
      };
    case "internships":
      return {
        ...base,
        category,
        duration: optional(fields.duration),
        compensation: optional(fields.compensation),
        stipend: optional(fields.stipend),
        skills,
      };
    default:
      return {
        ...base,
        category,
        stage: optional(fields.stage),
        examOn: date(fields.exam_on),
      };
  }
}

export function mapPage(raw: unknown) {
  const row = record(raw);
  if (
    !Array.isArray(row.items) ||
    !Number.isSafeInteger(row.page) ||
    !Number.isSafeInteger(row.total) ||
    !Number.isSafeInteger(row.limit)
  )
    throw new Error("Invalid catalogue page");
  const facets = Object.fromEntries(
    Object.entries(record(row.facets)).map(([key, value]) => [
      key,
      Array.isArray(value)
        ? value.filter((entry): entry is string => typeof entry === "string")
        : [],
    ]),
  );
  return {
    items: row.items.map(mapOpportunity),
    page: Number(row.page),
    total: Number(row.total),
    limit: Number(row.limit),
    facets,
  };
}
