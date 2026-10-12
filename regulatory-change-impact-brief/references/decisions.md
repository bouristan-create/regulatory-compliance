# Project decisions

Each decision is also written into the snapshot of the stage it governs (`decisions` array).

## DEC-01 — Review date is fixed; retrieval time is separate

- **Stage:** scope
- **Concern:** Sources are read in October but the review is as of 26 August 2026.
- **Options:** Use retrieval date as as-of date; Use assigned review date and record retrieval times separately
- **Source basis:** Assignment scenario; interview 03:34 PM ('The review is as of August 26, 2026').
- **Chosen behaviour:** as_of is always the --review-date; every source attempt records its actual retrieved_at.
- **Rationale:** Conclusions must be about the legal and factual position on the review date.
- **Trade-offs:** Later legal changes are not reflected unless the review date is changed by a human
- **Downstream effect:** Stage 03 checks each legal version was effective by the review date.

## DEC-02 — Read every disclosed route live; never substitute a local copy

- **Stage:** source-capture
- **Concern:** A failed read could tempt a fallback to stored files.
- **Options:** Fall back to the last good capture; Record the failure and continue with what is supportable
- **Source basis:** Starter README; interview 03:33 PM ('produce useful unaffected work while maintaining clear visibility on the limits').
- **Chosen behaviour:** Each run fetches all 10 routes with retries; failures are kept as attempts with null hash.
- **Rationale:** A stale copy would hide the gap the reviewers need to see.
- **Trade-offs:** A network outage yields a partial or blocked package instead of a complete one
- **Downstream effect:** Stage 03-05 mark dependent items unresolved; the brief lists the failure.

## DEC-03 — Binding basis is the OJ act plus the OJ amendment; consolidation is navigation only

- **Stage:** authority-and-timing
- **Concern:** Several legal routes say slightly different things about which text counts.
- **Options:** Rely on the Service Desk/consolidated text; Rely on OJ texts and cross-check navigation aids
- **Source basis:** Interview 03:34 PM: 'The July 27, 2026, consolidation is a navigation aid, not a separate legal act. We always check LAW, OJ, AMEND, and CONSOLIDATED.'
- **Chosen behaviour:** Art. 50 paragraphs are extracted from the OJ text; Art. 50(7) and Art. 111(4) from Regulation (EU) 2026/1744; consolidated and Service Desk texts are compared, not cited as binding.
- **Rationale:** Only the OJ publications are legally authentic.
- **Trade-offs:** More parsing of large EUR-Lex pages; If the OJ page changes layout the run blocks rather than falling back
- **Downstream effect:** Statutory register rows cite RULE-ART50-* evidence from the OJ source.

## DEC-04 — Field meanings are disclosed, not guessed

- **Stage:** evidence-reconciliation
- **Concern:** Register values could be renamed or extended.
- **Options:** Map unknown columns heuristically; Require the disclosed fields and report anything else
- **Source basis:** Interview 03:35 PM (status values) and policy CTRL-EVIDENCE-STATES.
- **Chosen behaviour:** Columns are found by header name (any order, extra columns allowed); missing fields or undisclosed values are reported as gaps.
- **Rationale:** Guessing a renamed field could silently change a business meaning.
- **Trade-offs:** A legitimate rename needs a config change before the run is complete
- **Downstream effect:** Unknown values become unresolved items with an owner.

## DEC-05 — Separate statutory and internal-policy rule bases

- **Stage:** impact-analysis
- **Concern:** Internal policy is stricter than Article 50 for deployers (e.g. notices for direct interaction).
- **Options:** Merge into one compliance verdict; Keep one row per system per rule basis
- **Source basis:** Interview 03:24 PM ('use the binding Article 50 text and the internal policy to evaluate our controls'); policy approval boundary.
- **Chosen behaviour:** Each register row has rule_ref and rule_basis; statutory rows go to Legal, policy rows to Operations.
- **Rationale:** Legal and Operations own different decisions; mixing bases would misstate legal exposure.
- **Trade-offs:** More rows for reviewers to read
- **Downstream effect:** Approval requirements are routed by rule basis.

## DEC-06 — Quillhaven's role is taken from the register and corroborated by the policy operating facts

- **Stage:** impact-analysis
- **Concern:** Provider duties (50(1), 50(2)) and deployer duties (50(3), 50(4)) differ.
- **Options:** Assume deployer for all; Use register role, corroborate with the policy context, unresolved when either is open
- **Source basis:** SYSTEMS provider_role/deployer_role; policy 'Operating scope' paragraph.
- **Chosen behaviour:** Deployer-only when both agree; unknown (AI-005) stays unresolved with the owner's refresh as the need.
- **Rationale:** Role decides which paragraph applies; it must not be assumed.
- **Trade-offs:** Conclusions for supplier products depend on owner-supplied facts that the policy says are not Legal decisions
- **Downstream effect:** Statutory no-impact rows explain that provider duties sit with the supplier and ask Legal to confirm.

## DEC-07 — Dates only from CALENDAR; undated proposals stay out of the .ics

- **Stage:** actions-and-approvals
- **Concern:** The automation could propose its own deadlines.
- **Options:** Invent target dates; Carry calendar dates forward unchanged and leave new proposals undated
- **Source basis:** Interview 03:32 PM (owners and dates live in the calendar sheet); policy approval boundary (may not change a production deadline).
- **Chosen behaviour:** Calendar actions become TENTATIVE events; new needs are undated proposals explained in register and brief.
- **Rationale:** Operations owns operational deadlines.
- **Trade-offs:** Some needs (e.g. AI-008 Art. 50(4) confirmation) have no date until an owner sets one
- **Downstream effect:** action-calendar.ics contains only calendar-backed dates.

## DEC-08 — Validated means internally consistent, not approved

- **Stage:** publication-validation
- **Concern:** A green validation could be read as sign-off.
- **Options:** Report 'published'; Report 'validated' with an explicit note and pending approvals
- **Source basis:** Assignment publication rules; interview 03:33 PM (no delivery claimed without evidence).
- **Chosen behaviour:** Stage 07 checks schema, chain, hashes and cross-file agreement; review requests are bound to the brief hash and marked prepared-not-sent.
- **Rationale:** Reviewers must be able to tell exactly which draft they are asked to approve.
- **Trade-offs:** Every rerun changes the brief hash, so earlier requests no longer match
- **Downstream effect:** Unmatched future feedback stays unresolved.
