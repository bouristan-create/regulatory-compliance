# Impact rules

The register keeps two **rule bases** apart. Each system gets one statutory row, plus one row for
each internal-policy control that applies to it.

## Statutory rows: Quillhaven's own duties under EU AI Act Article 50 (reviewer: Legal)

The binding text is Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744.

| Facts (register + policy operating facts) | State | Rule |
|---|---|---|
| Binding OJ or amendment text unavailable or unsuitable this run | `unresolved` | conclusion withheld |
| Provider role `unknown` (register) or not corroborated by the policy operating-scope paragraph | `unresolved` | 50(1)-(3) |
| Deployer only; emotion recognition / biometric categorisation `unknown` | `unresolved` | 50(3) |
| Deployer only; emotion recognition / biometric categorisation `yes` | `supported-impact` | 50(3), 50(5) |
| Deployer only; synthetic image/audio/video that is a deep fake (real people, could be taken as authentic) | `supported-impact` | 50(4) first subpara., 50(5) |
| Deployer only; synthetic media that is not a deep fake | `supported-no-impact` | 50(4); 50(2) marking is the supplier's provider duty |
| Deployer only; generated text not published to inform the public on matters of public interest | `supported-no-impact` | 50(4) second subpara. |
| Deployer only; direct interaction, no emotion/biometric use | `supported-no-impact` | 50(1) is a provider design duty; the policy notice rule is assessed separately |
| Anything not covered above | `unresolved` | output type not mapped |

The new Art. 111(4) transition to 2 December 2026 applies to **providers** of generative systems
placed on the market before 2 August 2026. It is reported as timing context and does not move
Quillhaven's deployer duties.

Every statutory row, including a no-impact row, gets a pending Legal review request, because Legal
owns the final interpretation.

## Internal-policy rows: AI-POL-2026-08-15 controls (reviewer: Operations; exceptions: Legal)

| Control | Applies when | State |
|---|---|---|
| Notice before/at first interaction | facts show direct interaction | open conflicting evidence → `conflicting`; notice `no` → `supported-impact`; notice `yes` + evidence complete + no open records → `supported-no-impact`; otherwise `unresolved` |
| Public synthetic media keep machine-readable provenance + visible label | `synthetic_*` and exposed to `public` | conflicting evidence → `conflicting`; partial/missing/stale or no visible label → `unresolved`; otherwise `supported-no-impact` |
| Staff-only drafting records how material reaches people | `output_type = text` | missing evidence or notice `unknown` → `unresolved`; `not_applicable` + complete → `supported-no-impact` |
| Register evidence is current | evidence `stale` | `unresolved` |
| Exception needs owner, rationale, expiry and Legal approval | an `exception_request` record exists | `unresolved` (the automation never approves one) |

## Actions

Calendar actions attach to a row by topic: notice/disclosure, provenance/label, recipient,
provider-role/release/evidence, or exception. A `supported-no-impact` row gets no action. A row that
needs an owner decision but has no calendar action gets an **undated** proposal (`PA-NEW-…`). That
proposal is explained in the register and the brief and left out of the `.ics`.
