# Regulatory Change Impact — Quillhaven Academy Article 50 review

This repository holds the `regulatory-change-impact-brief` Agent Skill. It prepares a review-ready
EU AI Act Article 50 package for Quillhaven Academy's Legal and Operations reviewers. It is read-only
and draft-only: Legal and Operations keep every decision.

## Run it (one end-to-end command)

Requires Python 3.10+ and one maintained library, `jsonschema`, which validates the snapshots
against the unchanged `snapshot.schema.json`.

```
pip install -r regulatory-change-impact-brief/scripts/requirements.txt
python regulatory-change-impact-brief/scripts/run_review.py --review-date 2026-08-26 --reason "first run"
```

- **Runtime:** about 1-2 minutes. Most of it is reading the large EUR-Lex pages, plus 20 s / 40 s
  waits before retrying a route that fails.
- **Setup:** network access to the routes in `regulatory-change-impact-brief/config/sources.json`.
  These are the routes the manager disclosed in the interview. No credentials are needed or stored.
- **Exit codes:** `0` validated, `3` blocked (binding legal authority unavailable; the package is
  consistent but statutory conclusions are withheld), `1` failed.
- **Check only:** `python regulatory-change-impact-brief/scripts/run_review.py --verify` re-inspects
  the snapshots, hashes and cross-file agreement without fetching anything.
- **Retry:** run the same command again with a new `--reason`. The previous run is moved to
  `deliverables/history/<old-run-id>/` and named in stage 01 `supersedes_run_id`.

## What it produces

| Path | Content |
|---|---|
| `deliverables/impact-register.csv` | One row per system per rule basis (statutory Article 50 vs internal policy AI-POL-2026-08-15) |
| `deliverables/compliance-brief.md` | Run ID, as-of date, recipients, source quality, observations, conflicts, proposed actions, decisions requested |
| `deliverables/action-calendar.ics` | Tentative all-day events for calendar-backed proposed actions only |
| `deliverables/snapshots/01…07-*.json` | The seven chained stage snapshots |
| `deliverables/sources/<run-id>/` | Captured bytes of every source used, plus `extracts.json` (claim-bearing extracts with locators) |
| `deliverables/history/` | Earlier runs, kept as they were |
| `interviews/` | The unedited Work Sim interview export |

How it decides is documented in `regulatory-change-impact-brief/references/`:
- `impact-rules.md`: the impact rules
- `field-meanings.md`: what each field means
- `decisions.md`: each project decision, with its options and trade-offs

## Known limits

- EUR-Lex sometimes answers automated reads with an AWS WAF bot challenge (HTTP 202, empty body).
  The skill records that as `unavailable`, does not try to bypass it, and blocks the statutory
  conclusions for that run. Re-run later.
- Company facts are the owner-supplied operating facts on the Operations policy page. They do not
  prove provenance, refresh stale evidence or settle applicability; Legal decides.

---

## Starter instructions (unchanged)

Build a reusable Skill that connects regulatory changes to company impacts and draft compliance actions.

## Start

1. Read the [formal assignment](https://private-pecorino-70e.notion.site/Project-B-Regulatory-Change-Impact-Compliance-Actions-Learner-assignment-3da0b700541e8152b6d1c638fd1c34fa?source=copy_link) for the work and acceptance requirements.
2. Create your own repository from [this starter](https://github.com/GitRollTraining/regulatory-compliance) using **Fork**, then clone your copy and work there.

## Supplied files

| File | Purpose |
|---|---|
| `README.md` | Starting instructions and links. |
| `snapshot.schema.json` | Public snapshot contract; keep it unchanged. |

Create the Skill, implementation and outputs described in the formal assignment. This starter supplies no business workflow implementation.

## Before you work

**Interview rule.** You conduct the stakeholder interview yourself, and the questions are yours. Do not connect a coding agent or any other AI to the interview to run, script, or automate it. The interview transcript is assessed together with the code; a project whose interview was run by an agent is not scored.

- Export your interview as the original Work Sim Markdown, save one final complete file per session under `interviews/`, and commit and push it with your code. Do not rewrite the export. If the export is unavailable, contact the facilitator.

- Use an Agent Skills-capable coding environment. Choose and document your implementation runtime and dependencies; no runtime or install command is supplied here.
- Follow the [shared course guide for session capture](https://classroom.google.com/c/ODcyMjA4NTkwNDk2/m/ODc0NzI2NzQzMzQ2/details) and verify capture is active before implementation. Keep credentials out of the repository.
- Meet the [stakeholder](https://work-sim.catalyte.ai/s/project-b-regulatory-compliance) to understand the work and relevant business sources. Read those online sources through their intended access route; an unavailable source is not permission to substitute repository data.
