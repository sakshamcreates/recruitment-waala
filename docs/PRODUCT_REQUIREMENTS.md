# Recruitment Waala product requirements

**Every Opportunity. One Platform.**

Recruitment Waala helps people in India discover and track government recruitment,
corporate roles, internships and career updates. A candidate should be able to
identify the issuing organisation, distinguish recruitment cycles and reach the
official application or notification page.

## Audiences and module requirements

| Module | Requirement |
| --- | --- |
| Government jobs | Show authority, notification reference, cycle, eligibility, application window and official link. Preserve corrigenda. |
| Admit cards, results, answer keys and syllabus | Link each notice to the actual recruitment cycle and identify the exam stage, issue date and issuing body. Link to the authority for individual results. |
| Corporate jobs | Identify the employer, requisition, employment type, location, workplace mode and employer-owned application link. |
| Internships | Capture duration, eligibility, location and stipend with currency and interval when disclosed. |
| Search and filtering | Support query, category, employer, geography and current availability. Provide stable ordering and cursor pagination. |
| Accounts and saved jobs | Allow anonymous discovery. Signed-in users can save and unsave opportunities and see subsequent status changes. |
| Job alerts | Allow opt-in subscriptions to filters with cadence and unsubscribe controls. Avoid duplicate deliveries. |
| Admin moderation | Give authorised reviewers evidence, disposition and correction workflows with an audit trail. |
| Automated ingestion | Collect only from approved sources with per-source limits, idempotent retries and failure visibility. |
| Source verification and update history | Attribute published items to evidence and show material corrections, deadline changes and withdrawals. |

Career updates use the same opportunity model and carry their own topic and issue
date. The platform sends applicants to official destinations. Application processing,
payments and hosting candidate-level admit-card or result records are outside scope.

## Acceptance criteria

- Two rounds with the same title and employer appear separately when they represent
  different cycles. Repeated observations of the same cycle can support one record.
- Expired and withdrawn opportunities stop appearing in default active results, and
  their detail pages retain status and publication history.
- Application deadlines preserve the source time zone and distinguish missing times
  from a stated cutoff. User-facing Indian local dates use Asia/Kolkata when applicable.
- A user can reach the official evidence and see when it was verified.
- Moderation decisions retain reasons. Candidate-private account data stays private.
- Discovery supports keyboard navigation and accessible labels.

Phase 0 acceptance is a bootable foundation, health surfaces, a reversible empty
schema, local infrastructure, automated checks and reviewed designs. Success
measures for later phases include time from official publication to verified
listing, deadline correction latency, and sampled false-merge and stale-listing rates.
