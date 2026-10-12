# Article 50 compliance brief — DRAFT for review

- **Run ID:** RUN-20261012T201652Z
- **As-of (review) date:** 2026-08-26 (sources retrieved 2026-10-12T20:16:58Z to 2026-10-12T20:20:03Z)
- **Recipients:** Legal (final interpretation of the EU AI Act; exceptions) and Operations (policy activation, approved dates, incident closure). Prepared by the Compliance and Operations Manager. No delivery is claimed.
- **Status:** review-ready draft; run status `blocked`. Nothing here is legal advice, an approval, an activated policy or a changed deadline.
- **Package:** `impact-register.csv`, `action-calendar.ics`, snapshots in `snapshots/`. File hashes and review-request bindings are recorded in `snapshots/07-publication-validation.json`.

## Source quality and limitations

| Source | Role | Status | Version | Retrieved |
|---|---|---|---|---|
| SRC-ART50-SD | official-guidance | retrieved | 2026-07-27 | 2026-10-12T20:16:58Z |
| SRC-LAW-OJ | binding-regulation | unavailable | SourceUnavailable: HTTP 202 bot-protection challenge (x-amzn-waf-action) instead of the document | 2026-10-12T20:17:59Z |
| SRC-LAW-AMEND | binding-regulation | unavailable | SourceUnavailable: HTTP 202 bot-protection challenge (x-amzn-waf-action) instead of the document | 2026-10-12T20:18:59Z |
| SRC-LAW-CONS | other | unavailable | SourceUnavailable: HTTP 202 bot-protection challenge (x-amzn-waf-action) instead of the document | 2026-10-12T20:19:59Z |
| SRC-TIMELINE | official-guidance | retrieved | sha256:28f0a7b623182b2f16da79dca8b628b5ef10233a0bcb8def1f83da0a8a231127 | 2026-10-12T20:20:00Z |
| SRC-GUIDANCE | official-guidance | retrieved | sha256:6caab6077e53b5a6d966f38d1b9dc922f490a5e2b388ff92971513dbaa55069b | 2026-10-12T20:20:00Z |
| SRC-POLICY | internal-policy | retrieved | AI-POL-2026-08-15 | 2026-10-12T20:20:00Z |
| SRC-SYSTEMS | operational-record | retrieved | register-2026-08-26 | 2026-10-12T20:20:01Z |
| SRC-EVIDENCE | operational-record | retrieved | sha256:3dacdd595cbbdb17749bc879b01f197d2c5691ab5e2385aacef797ebdea7295b | 2026-10-12T20:20:02Z |
| SRC-CALENDAR | operational-record | retrieved | calendar-2026-08-26 | 2026-10-12T20:20:03Z |

- Binding basis: Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744, which was in force before the review date. The 27 July 2026 consolidation and the Service Desk page are navigation aids that were cross-checked, not relied on as the act.
- Company facts come from the Operations operating-facts context in the policy page, which records owner-supplied facts. Per that page, it does not prove provenance, refresh stale evidence or settle statutory applicability.
- **Binding legal authority was unavailable or unsuitable this run.** Formal Article 50 conclusions are withheld (statutory rows unresolved). Policy-basis work continues, as the manager asked for useful unaffected work.
- Technical failure: SRC-LAW-OJ at source-capture: SourceUnavailable: HTTP 202 bot-protection challenge (x-amzn-waf-action) instead of the document. Recovery: Re-run the documented command; if it persists, report the unavailable route to the source owner / facilitator.
- Technical failure: SRC-LAW-AMEND at source-capture: SourceUnavailable: HTTP 202 bot-protection challenge (x-amzn-waf-action) instead of the document. Recovery: Re-run the documented command; if it persists, report the unavailable route to the source owner / facilitator.
- Technical failure: SRC-LAW-CONS at source-capture: SourceUnavailable: HTTP 202 bot-protection challenge (x-amzn-waf-action) instead of the document. Recovery: Re-run the documented command; if it persists, report the unavailable route to the source owner / facilitator.

## Supported observations

Each conclusion is scoped either to **Quillhaven's own statutory duties under Article 50** or to **internal policy AI-POL controls**. The two are different rule bases.

### Supported impacts

- **IMP-AI-004-NOTICE** (internal policy (internal control); AI-POL-2026-08-15: Learner and public transparency [CTRL-NOTICE]): No first-interaction AI notice; confirmed by evidence: First interaction contains no AI notice. Evidence: EV-CALENDAR-ACT001, EV-EVIDENCE-REC004, EV-POLICY-CTRLNOTICE, EV-SYSTEMS-AI004.

### Supported no-impact

- **IMP-AI-001-NOTICE** (internal policy (internal control); AI-POL-2026-08-15: Learner and public transparency [CTRL-NOTICE]): Notice in place and evidence complete: Notice screenshot and release record agree. Evidence: EV-EVIDENCE-REC001, EV-POLICY-CTRLNOTICE, EV-SYSTEMS-AI001.
- **IMP-AI-006-STAFF-DRAFT** (internal policy (internal control); AI-POL-2026-08-15: Learner and public transparency [CTRL-STAFF-DRAFT]): Staff-only use, outputs not sent outside the staff workspace; evidence complete. Evidence: EV-EVIDENCE-REC007, EV-POLICY-CTRLSTAFFDRAFT, EV-SYSTEMS-AI006.

## Conflicts and unresolved scope

- **IMP-AI-003-SYNTHETIC** — conflicting (AI-POL-2026-08-15: Learner and public transparency [CTRL-SYNTHETIC]). Visible label recorded but provenance evidence conflicts: Visible label exists but exported platform copy may have lost metadata. A visible label does not prove machine-readable provenance. **Needed:** Communications verifies provenance on the published copy. **Owner:** Communications. Evidence: EV-CALENDAR-ACT004, EV-EVIDENCE-REC003, EV-POLICY-CTRLSYNTHETIC, EV-SYSTEMS-AI003.
- **IMP-AI-007-NOTICE** — conflicting (AI-POL-2026-08-15: Learner and public transparency [CTRL-NOTICE]). Register says notice='no' but evidence conflicts: Owner says a banner exists but the current capture shows none. The stylised graphic alone does not establish what visitors understand. **Needed:** System owner resolves which account of the notice is current. **Owner:** Marketing. Evidence: EV-CALENDAR-ACT002, EV-EVIDENCE-REC008, EV-POLICY-CTRLNOTICE, EV-SYSTEMS-AI007.
- **IMP-AI-001-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-POLICY-AI001, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI001.
- **IMP-AI-002-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-CALENDAR-ACT003, EV-POLICY-AI002, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI002.
- **IMP-AI-002-STAFF-DRAFT** — unresolved (AI-POL-2026-08-15: Learner and public transparency [CTRL-STAFF-DRAFT]). Owner has not recorded how generated material reaches recipients: No evidence that recipients are told when generated text is used. Missing evidence is not converted to compliance or non-compliance. **Needed:** Owner records the recipient disclosure practice; Legal confirms. **Owner:** Admissions. Evidence: EV-CALENDAR-ACT003, EV-EVIDENCE-REC002, EV-POLICY-CTRLSTAFFDRAFT, EV-SYSTEMS-AI002.
- **IMP-AI-003-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-POLICY-AI003, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI003.
- **IMP-AI-004-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-POLICY-AI004, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI004.
- **IMP-AI-005-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-CALENDAR-ACT005, EV-POLICY-AI005, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI005.
- **IMP-AI-005-EVIDENCE-CURRENCY** — unresolved (AI-POL-2026-08-15: Evidence and exceptions [CTRL-REGISTER]). Evidence is stale (last updated 2026-04-15): Provider role questionnaire predates the current release. **Needed:** Owner refreshes role and release evidence for the current release. **Owner:** Assessment Operations. Evidence: EV-CALENDAR-ACT005, EV-EVIDENCE-REC005, EV-EVIDENCE-REC006, EV-POLICY-CTRLREGISTER.
- **IMP-AI-006-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-POLICY-AI006, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI006.
- **IMP-AI-007-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-POLICY-AI007, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI007.
- **IMP-AI-008-ART50** — unresolved (EU AI Act Art. 50). Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld. **Needed:** Re-run with the binding OJ and amendment texts retrieved. **Owner:** Legal. Evidence: EV-POLICY-AI008, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI008.
- **IMP-AI-008-SYNTHETIC** — unresolved (AI-POL-2026-08-15: Learner and public transparency [CTRL-SYNTHETIC]). Label state 'visible_label'; provenance not verified: Visible label verified but machine-readable provenance not checked. **Needed:** Communications completes the provenance test. **Owner:** Communications. Evidence: EV-CALENDAR-ACT006, EV-EVIDENCE-REC009, EV-EVIDENCE-REC010, EV-POLICY-CTRLSYNTHETIC.
- **IMP-AI-008-EXCEPTION** — unresolved (AI-POL-2026-08-15: Evidence and exceptions [CTRL-EXCEPTION]). Exception request REC-010 is draft: No Legal approval or expiry date recorded. The automation may not approve it. **Needed:** Legal decides the exception; it needs a named owner, rationale, expiry date and Legal approval. **Owner:** Legal. Evidence: EV-CALENDAR-ACT007, EV-EVIDENCE-REC010, EV-POLICY-CTRLEXCEPTION.

### Escalations

- **ESC-IMP-AI-008-EXCEPTION** (Legal): Draft exception request without Legal approval or expiry date
- **ESC-AI-005-SCOPE** (Legal): AI-005 biometric/emotion facts are open. If the flagging infers emotions of learners, questions outside Article 50 (e.g. Article 5 prohibitions) may arise; this review draws no conclusion on them.

## Proposed actions and dates

Dates come only from the CALENDAR register and are carried forward unchanged as tentative proposals. Undated proposals are not in the calendar file.

| Action | System | Responsible | Proposed date | In .ics | Approval | Linked impacts |
|---|---|---|---|---|---|---|
| ACT-001: Add and verify first-interaction AI notice | AI-004 | Learning Experience | 2026-09-04 | yes | pending (Operations) | IMP-AI-004-NOTICE |
| ACT-002: Resolve disclosure evidence conflict | AI-007 | Marketing | 2026-09-03 | yes | pending (Operations) | IMP-AI-007-NOTICE |
| ACT-003: Confirm recipient disclosure practice | AI-002 | Admissions | 2026-09-08 | yes | pending (Legal) | IMP-AI-002-ART50, IMP-AI-002-STAFF-DRAFT |
| ACT-004: Verify machine-readable provenance after publishing | AI-003 | Communications | 2026-09-10 | yes | pending (Operations) | IMP-AI-003-SYNTHETIC |
| ACT-005: Refresh provider-role and release evidence | AI-005 | Assessment Operations | 2026-09-12 | yes | pending (Legal) | IMP-AI-005-ART50, IMP-AI-005-EVIDENCE-CURRENCY |
| ACT-006: Complete provenance test | AI-008 | Communications | 2026-09-09 | yes | pending (Operations) | IMP-AI-008-SYNTHETIC |
| ACT-007: Review exception request | AI-008 | Legal | 2026-09-15 | yes | pending (Legal) | IMP-AI-008-EXCEPTION |
| ACT-008: Quarterly AI register evidence review | ALL | Operations | 2026-10-02 | yes | pending (Operations) | - |
| PA-NEW-AI-001-ART50: Legal to address: Re-run with the binding OJ and amendment texts retrieved. | AI-001 | Legal | undated | no — No owner-approved date exists in CALENDAR; the automation does not invent deadlines. | pending (Legal) | IMP-AI-001-ART50 |
| PA-NEW-AI-003-ART50: Legal to address: Re-run with the binding OJ and amendment texts retrieved. | AI-003 | Legal | undated | no — No owner-approved date exists in CALENDAR; the automation does not invent deadlines. | pending (Legal) | IMP-AI-003-ART50 |
| PA-NEW-AI-004-ART50: Legal to address: Re-run with the binding OJ and amendment texts retrieved. | AI-004 | Legal | undated | no — No owner-approved date exists in CALENDAR; the automation does not invent deadlines. | pending (Legal) | IMP-AI-004-ART50 |
| PA-NEW-AI-006-ART50: Legal to address: Re-run with the binding OJ and amendment texts retrieved. | AI-006 | Legal | undated | no — No owner-approved date exists in CALENDAR; the automation does not invent deadlines. | pending (Legal) | IMP-AI-006-ART50 |
| PA-NEW-AI-007-ART50: Legal to address: Re-run with the binding OJ and amendment texts retrieved. | AI-007 | Legal | undated | no — No owner-approved date exists in CALENDAR; the automation does not invent deadlines. | pending (Legal) | IMP-AI-007-ART50 |
| PA-NEW-AI-008-ART50: Legal to address: Re-run with the binding OJ and amendment texts retrieved. | AI-008 | Legal | undated | no — No owner-approved date exists in CALENDAR; the automation does not invent deadlines. | pending (Legal) | IMP-AI-008-ART50 |

## Decisions requested from Legal and Operations

Review requests are prepared here and have **not been sent**. The binding of each request to the exact hash of this brief is recorded in `snapshots/07-publication-validation.json`.

| Request | Reviewer | Subject | Question | Evidence |
|---|---|---|---|---|
| RR-001 | Legal | IMP-AI-001-ART50 (actions: PA-NEW-AI-001-ART50) | What evidence or decision resolves this item, and who supplies it? | EV-POLICY-AI001, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI001 |
| RR-002 | Legal | IMP-AI-002-ART50 (actions: ACT-003) | What evidence or decision resolves this item, and who supplies it? | EV-CALENDAR-ACT003, EV-POLICY-AI002, EV-POLICY-OPERATINGSCOPE |
| RR-003 | Operations | IMP-AI-002-STAFF-DRAFT (actions: ACT-003) | What evidence or decision resolves this item, and who supplies it? | EV-CALENDAR-ACT003, EV-EVIDENCE-REC002, EV-POLICY-CTRLSTAFFDRAFT |
| RR-004 | Legal | IMP-AI-003-ART50 (actions: PA-NEW-AI-003-ART50) | What evidence or decision resolves this item, and who supplies it? | EV-POLICY-AI003, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI003 |
| RR-005 | Operations | IMP-AI-003-SYNTHETIC (actions: ACT-004) | Which account is current, and does the proposed action resolve the conflict? | EV-CALENDAR-ACT004, EV-EVIDENCE-REC003, EV-POLICY-CTRLSYNTHETIC |
| RR-006 | Legal | IMP-AI-004-ART50 (actions: PA-NEW-AI-004-ART50) | What evidence or decision resolves this item, and who supplies it? | EV-POLICY-AI004, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI004 |
| RR-007 | Operations | IMP-AI-004-NOTICE (actions: ACT-001) | Do you accept this supported impact and the proposed action/date? | EV-CALENDAR-ACT001, EV-EVIDENCE-REC004, EV-POLICY-CTRLNOTICE |
| RR-008 | Legal | IMP-AI-005-ART50 (actions: ACT-005) | What evidence or decision resolves this item, and who supplies it? | EV-CALENDAR-ACT005, EV-POLICY-AI005, EV-POLICY-OPERATINGSCOPE |
| RR-009 | Operations | IMP-AI-005-EVIDENCE-CURRENCY (actions: ACT-005) | What evidence or decision resolves this item, and who supplies it? | EV-CALENDAR-ACT005, EV-EVIDENCE-REC005, EV-EVIDENCE-REC006 |
| RR-010 | Legal | IMP-AI-006-ART50 (actions: PA-NEW-AI-006-ART50) | What evidence or decision resolves this item, and who supplies it? | EV-POLICY-AI006, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI006 |
| RR-011 | Legal | IMP-AI-007-ART50 (actions: PA-NEW-AI-007-ART50) | What evidence or decision resolves this item, and who supplies it? | EV-POLICY-AI007, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI007 |
| RR-012 | Operations | IMP-AI-007-NOTICE (actions: ACT-002) | Which account is current, and does the proposed action resolve the conflict? | EV-CALENDAR-ACT002, EV-EVIDENCE-REC008, EV-POLICY-CTRLNOTICE |
| RR-013 | Legal | IMP-AI-008-ART50 (actions: PA-NEW-AI-008-ART50) | What evidence or decision resolves this item, and who supplies it? | EV-POLICY-AI008, EV-POLICY-OPERATINGSCOPE, EV-SYSTEMS-AI008 |
| RR-014 | Operations | IMP-AI-008-SYNTHETIC (actions: ACT-006) | What evidence or decision resolves this item, and who supplies it? | EV-CALENDAR-ACT006, EV-EVIDENCE-REC009, EV-EVIDENCE-REC010 |
| RR-015 | Legal | IMP-AI-008-EXCEPTION (actions: ACT-007) | What evidence or decision resolves this item, and who supplies it? | EV-CALENDAR-ACT007, EV-EVIDENCE-REC010, EV-POLICY-CTRLEXCEPTION |

Source versions for every request: SRC-ART50-SD=2026-07-27; SRC-LAW-OJ=None; SRC-LAW-AMEND=None; SRC-LAW-CONS=None; SRC-TIMELINE=sha256:28f0a7b623182b2f16da79dca8b628b5ef10233a0bcb8def1f83da0a8a231127; SRC-GUIDANCE=sha256:6caab6077e53b5a6d966f38d1b9dc922f490a5e2b388ff92971513dbaa55069b; SRC-POLICY=AI-POL-2026-08-15; SRC-SYSTEMS=register-2026-08-26; SRC-EVIDENCE=sha256:3dacdd595cbbdb17749bc879b01f197d2c5691ab5e2385aacef797ebdea7295b; SRC-CALENDAR=calendar-2026-08-26.
