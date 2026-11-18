export const categories = {
  "government-jobs": {
    label: "Government jobs",
    short: "Government",
    description:
      "Recruitment notices, eligibility and application dates from public sector employers.",
  },
  "corporate-jobs": {
    label: "Corporate jobs",
    short: "Corporate",
    description:
      "Explore roles by experience, location, skills and workplace mode.",
  },
  internships: {
    label: "Internships",
    short: "Internships",
    description:
      "Find early-career roles by duration, location and compensation.",
  },
  results: {
    label: "Results",
    short: "Results",
    description:
      "Find exam outcomes by recruiting body, examination and stage.",
  },
  "admit-cards": {
    label: "Admit cards",
    short: "Admit cards",
    description:
      "Find exam hall ticket notices by issuing body and exam stage.",
  },
  "answer-keys": {
    label: "Answer keys",
    short: "Answer keys",
    description: "Find provisional and final answer key notices.",
  },
  syllabus: {
    label: "Syllabus",
    short: "Syllabus",
    description: "Explore syllabus and exam pattern notices.",
  },
} as const;

export type Category = keyof typeof categories;
export const primaryCategories = [
  "government-jobs",
  "corporate-jobs",
  "internships",
  "results",
  "admit-cards",
] as const;
export const examCategories = [
  "results",
  "admit-cards",
  "answer-keys",
  "syllabus",
] as const;
export type ExamCategory = (typeof examCategories)[number];
export const categoryKeys = Object.keys(categories) as Category[];

export function isCategory(value: string): value is Category {
  return Object.hasOwn(categories, value);
}
