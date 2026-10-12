# Field meanings

The meanings below come from the interview
(`interviews/project-b-regulatory-compliance-20261012-1939.md`) and the Operations policy page
(AI-POL-2026-08-15). Columns are matched by header name: order does not matter and extra columns are
kept and listed. A missing required field, a duplicate column or an undisclosed value is reported as
a gap. Such values are never guessed.

## SYSTEMS (AI system register)

| Field | Meaning |
|---|---|
| `system_id` | Stable system ID (AI-001 …). The key across all three sheets. |
| `system_name`, `use_case`, `owner` | Internal inventory label, actual use and responsible owner. |
| `provider_role`, `deployer_role` | `yes` / `no` / `unknown`. `unknown` stays unresolved. |
| `exposed_group` | Who meets the output (learners, applicants, public, staff). |
| `output_type` | `direct_interaction`, `text`, `synthetic_image`, `synthetic_audio_video`, `classification`. |
| `current_notice` | `yes`, `no`, `unknown`, `visible_label`, `not_applicable` (interview 03:35 PM). A visible label does **not** prove machine-readable provenance. |
| `human_review` | The human-review path. |
| `evidence_status` | `complete`, `partial`, `missing`, `stale`, `conflicting`, `not_applicable`. These are distinct states (policy, "Evidence and exceptions"). |
| `evidence_updated_at` | Date of the last evidence update (YYYY-MM-DD). |
| `record_version` | Register version label, kept as the source version. |

## EVIDENCE (incident, gap, evidence and exception records)

| Field | Meaning |
|---|---|
| `record_id` | Stable record ID (REC-…). |
| `system_id` | The system the record is about. |
| `record_type` | `evidence`, `evidence_gap`, `incident`, `exception_request`. |
| `reported_at`, `owner`, `status` | Report date, owner, and `open` / `closed` / `draft`. Only Operations closes an incident. |
| `evidence_ref`, `evidence_state`, `notes` | Pointer to the evidence, its state (same vocabulary as above), and the owner's note. |

## CALENDAR (actions by owner, due date, status and review requirements)

| Field | Meaning |
|---|---|
| `action_id` | Stable action ID (ACT-…). Also the calendar UID stem. |
| `system_id` | System, or `ALL`. |
| `action`, `owner` | What is proposed, and who is responsible. |
| `due_date` | Proposed date (YYYY-MM-DD), carried forward unchanged. |
| `status` | `planned`, `open`, `blocked`, `scheduled` (as recorded). |
| `approval_required` | `legal` or `operations`: whose decision the action needs. |
| `source_version` | Calendar version label. |

## Policy page

The policy is located by meaning, not by position: the notice, synthetic-media, staff-drafting,
register, evidence-states, exception and approval-boundary clauses. The "Article 50 review — company
operating facts" section gives owner-supplied facts for each system. Per the page itself, those facts
do not prove provenance, refresh stale evidence or settle statutory applicability.
