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
  status?: "published" | "expired" | "withdrawn";
  applyUrl?: string;
  provenance:
    | { kind: "illustrative" }
    | {
        kind: "official";
        source: string;
        officialUrl?: string;
        verifiedOn?: string;
      };
};

export type GovernmentJob = BaseOpportunity & {
  category: "government-jobs";
  reference?: string;
  qualification?: string;
  employment?: string;
  age?: string;
  fee?: string;
  vacancies?: number;
  salary?: string;
};

export type CorporateJob = BaseOpportunity & {
  category: "corporate-jobs";
  experience?: string;
  mode?: string;
  employment?: string;
  skills: readonly string[];
  salary?: string;
};

export type Internship = BaseOpportunity & {
  category: "internships";
  duration?: string;
  compensation?: string;
  skills: readonly string[];
  stipend?: string;
};

export type ExamNotice = BaseOpportunity & {
  category: ExamCategory;
  stage?: string;
  examOn?: string;
};

export type Opportunity =
  GovernmentJob | CorporateJob | Internship | ExamNotice;
