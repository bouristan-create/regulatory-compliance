---
name: regulatory-change-impact-brief
description: Prepare Quillhaven Academy's review-ready EU AI Act Article 50 change-impact package for Legal and Operations. Use when asked to run, refresh or check the Article 50 review, impact register, compliance brief or draft action calendar. Reads the disclosed official legal routes and company registers live on every run, writes seven chained stage snapshots, and produces impact-register.csv, compliance-brief.md and action-calendar.ics as drafts. Never gives final legal advice, approves exceptions, activates policy, changes deadlines, closes incidents, sends responses or writes to a production calendar.
---

# Regulatory change impact brief (Article 50)

You prepare a **draft** package. Legal and Operations keep every decision.

## Run it

From the repository root:

```
pip install -r regulatory-change-impact-brief/scripts/requirements.txt
python regulatory-change-impact-brief/scripts/run_review.py --review-date 2026-08-26 --reason "<why this run>"
```

- `--review-date` is the assigned as-of date. Do not change it unless a human asks you to.
- `--reason` goes into stage 01 (`change_or_retry_reason`). Give the real reason, for example "first run", "retry after EUR-Lex challenge" or "CALENDAR updated".
- `--sources` and `--scope` take other JSON files. Use them only when an owner discloses a new route or scope.
- `--verify` inspects the current package without fetching anything.

Exit codes: `0` means validated, `3` means blocked (binding legal authority unavailable; package consistent), `1` means failed.

## What the run does

| Stage | Snapshot | What happens |
|---|---|---|
| 01 | `scope` | Records the review date, the 8 systems in scope, audiences and approval gates. If a previous run exists, it is moved to `deliverables/history/<old-run-id>/` and named in `supersedes_run_id`. |
| 02 | `source-capture` | Every route in `config/sources.json` is read live, with polite retries. Every attempt is recorded, including failed ones. The bytes are saved in `deliverables/sources/<run-id>/` and the extracts with locators in `extracts.json`. |
| 03 | `authority-and-timing` | Article 50(1)-(6) comes from the OJ text of Regulation (EU) 2024/1689. Art. 50(7), new Art. 111(4) and the entry into force come from Regulation (EU) 2026/1744. The consolidated text and the Service Desk page are cross-check only. |
| 04 | `evidence-reconciliation` | SYSTEMS, EVIDENCE, CALENDAR and the policy page are reconciled. Conflicts and gaps are kept, and missing evidence is never converted into a finding. |
| 05 | `impact-analysis` | Each system gets one statutory row (Quillhaven's own Art. 50 duties) and its internal-policy rows. |
| 06 | `actions-and-approvals` | Calendar actions are carried forward unchanged. Needs that have no calendar action become undated proposals. Review requests are prepared but not sent. |
| 07 | `publication-validation` | Checks schema, chain, hashes and cross-file agreement, then binds each review request to the brief's hash. |

## Rules you must keep

- **Live sources only.** If a route fails, it stays failed in the record. Do not substitute a local or earlier copy, and do not try to bypass bot protection (EUR-Lex sometimes answers with an AWS WAF challenge). Re-run later with a `--reason`.
- **Binding legal authority missing** means the run is `blocked`. Statutory rows stay unresolved, and the policy-basis work and calendar dates still go out. This is the manager's instruction: "produce useful unaffected work".
- **Field meanings are fixed** (see `references/field-meanings.md`). Columns may be reordered or extra, but a missing or renamed field, or an undisclosed value, is reported and never guessed.
- **Dates come only from CALENDAR.** Never invent or move a deadline.
- **Feedback.** Apply a reviewer response only if it arrives through the facilitator's verified channel and matches a request ID, the run and the brief hash. Otherwise leave it unresolved. Never simulate a reply.

## Files

- `config/sources.json`: the source routes disclosed in the interview (with interview timestamps)
- `config/scope.json`: systems in scope, audiences, approval gates
- `references/field-meanings.md`: what the register fields and values mean
- `references/impact-rules.md`: how each statutory and policy state is decided
- `references/decisions.md`: the project decisions with options and trade-offs
- `scripts/run_review.py`: the implementation (Python 3.10+, jsonschema)
