import type { ExamCategory } from "./categories.ts";

type BaseOpportunity = {
  id: string;
  title: string;
  organisation: string;
  summary: string;
  publishedOn: string;
  state?: string;
  location?: string;
  deadline?: string;
  provenance: { kind: "illustrative" };
};

export type GovernmentJob = BaseOpportunity & {
  category: "government-jobs";
  reference: string;
  qualification: string;
  employment: "Permanent" | "Contract";
  age?: string;
  fee?: string;
  vacancies?: number;
  salary?: string;
};

export type CorporateJob = BaseOpportunity & {
  category: "corporate-jobs";
  experience: string;
  mode: "On-site" | "Hybrid" | "Remote";
  employment: "Full-time" | "Contract";
  skills: readonly string[];
  salary?: string;
};

export type Internship = BaseOpportunity & {
  category: "internships";
  duration: string;
  compensation: "Paid" | "Unpaid";
  skills: readonly string[];
  stipend?: string;
};

export type ExamNotice = BaseOpportunity & {
  category: ExamCategory;
  stage: string;
  examOn?: string;
};

export type Opportunity =
  GovernmentJob | CorporateJob | Internship | ExamNotice;
