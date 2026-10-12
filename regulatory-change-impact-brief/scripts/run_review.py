#!/usr/bin/env python3
"""Regulatory change impact brief: EU AI Act Article 50 review for Quillhaven Academy.

Reads every disclosed source live (official EU legal routes, the Operations policy page and the
SYSTEMS / EVIDENCE / CALENDAR registers), writes seven chained stage snapshots, and produces a
review-ready draft package:

    deliverables/impact-register.csv
    deliverables/compliance-brief.md
    deliverables/action-calendar.ics

Read-only. It never writes to a source, gives final legal advice, activates policy, changes an
approved deadline, closes an incident, sends an official response or writes to a production
calendar. Legal and Operations keep every decision.

Runtime: Python 3.10+ and jsonschema (see requirements.txt).

Usage (from the repository root):
    python regulatory-change-impact-brief/scripts/run_review.py \
        --review-date 2026-08-26 --reason "first run"
    python regulatory-change-impact-brief/scripts/run_review.py --verify
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html.parser
import io
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = SKILL_DIR.parent
DEFAULT_SOURCES = SKILL_DIR / "config" / "sources.json"
DEFAULT_SCOPE = SKILL_DIR / "config" / "scope.json"
DEFAULT_SCHEMA = REPO_DIR / "snapshot.schema.json"
DEFAULT_OUT = REPO_DIR / "deliverables"

SCHEMA_VERSION = "regulatory-compliance-stage-snapshot/2"
STAGES = [
    "scope", "source-capture", "authority-and-timing", "evidence-reconciliation",
    "impact-analysis", "actions-and-approvals", "publication-validation",
]
FINAL_FILES = {
    "ART-REGISTER": "impact-register.csv",
    "ART-BRIEF": "compliance-brief.md",
    "ART-CALENDAR": "action-calendar.ics",
}
REGISTER_COLUMNS = [
    "impact_id", "system_id", "rule_ref", "state", "evidence_ids", "reason", "owner",
    "proposed_action", "proposed_due_date", "approval_status",
    # extra columns (allowed by the assignment)
    "system_name", "rule_basis", "action_ids", "resolution_need", "run_id",
]
USER_AGENT = "regulatory-change-impact-brief/1.0 (read-only review automation)"
UID_DOMAIN = "regulatory-change-impact-brief.quillhaven.invalid"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_DIR).as_posix()


def norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def ev_id(*parts: str) -> str:
    return "EV-" + "-".join(re.sub(r"[^A-Za-z0-9]+", "", p.upper()) or "X" for p in parts)


# ---------------------------------------------------------------------------
# Fetching. Every attempt is recorded, including failures.
# ---------------------------------------------------------------------------


class HtmlText(html.parser.HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "td", "table", "section"}

    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []
        self.skip = 0
        self.title: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if not self.skip:
            self.out.append(data)


def html_to_text(raw: bytes) -> tuple[str, str]:
    p = HtmlText()
    p.feed(raw.decode("utf-8", errors="replace"))
    text = re.sub(r"[ \t\xa0]+", " ", "".join(p.out))
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text, norm_space("".join(p.title))


def http(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 90):
    h = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json,text/csv;q=0.9,*/*;q=0.8"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status, hdrs, body = resp.status, dict(resp.headers), resp.read()
        if hdrs.get("x-amzn-waf-action") or hdrs.get("X-Amzn-Waf-Action"):
            # Bot-protection challenge instead of the document. Recorded as unavailable; never bypassed.
            raise SourceUnavailable(f"HTTP {status} bot-protection challenge (x-amzn-waf-action) instead of the document")
        if status != 200:
            raise SourceUnavailable(f"HTTP {status} with {len(body)} bytes instead of the document")
        return status, hdrs, body, resp.geturl()


class SourceUnavailable(Exception):
    """The route answered, but not with the requested document."""


def notion_page_id(url: str) -> str:
    m = re.search(r"([0-9a-f]{32})(?:\?|$)", url)
    if not m:
        raise ValueError(f"no Notion page id in {url}")
    h = m.group(1)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def sheet_export_url(url: str) -> str:
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url)
    if not m:
        raise ValueError(f"not a Google Sheets URL: {url}")
    gid = re.search(r"[#&?]gid=(\d+)", url)
    out = f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv"
    return out + (f"&gid={gid.group(1)}" if gid else "")


def fetch_once(src: dict) -> tuple[bytes, str, str, dict]:
    """Return (body, content_type, effective_url, headers) or raise."""
    kind = src["kind"]
    if kind == "html":
        status, headers, body, eff = http(src["url"])
        return body, headers.get("Content-Type", ""), eff, headers
    if kind == "sheet":
        status, headers, body, eff = http(sheet_export_url(src["url"]))
        return body, headers.get("Content-Type", ""), eff, headers
    if kind == "notion":
        host = re.match(r"(https://[^/]+)", src["url"]).group(1)
        payload = json.dumps({
            "page": {"id": notion_page_id(src["url"])}, "limit": 200,
            "cursor": {"stack": []}, "verticalColumns": False,
        }).encode()
        status, headers, body, eff = http(
            f"{host}/api/v3/loadCachedPageChunkV2", data=payload,
            headers={"Content-Type": "application/json"})
        return body, headers.get("Content-Type", ""), src["url"] + " (public page API)", headers
    raise ValueError(f"unknown source kind {kind!r}")


# ---------------------------------------------------------------------------
# Parsers. A source is accepted only after its identity is verified.
# ---------------------------------------------------------------------------


def parse_sheet(body: bytes, src: dict) -> dict:
    text = body.decode("utf-8-sig")
    table = [r for r in csv.reader(io.StringIO(text))]
    if not table:
        raise ValueError("empty sheet")
    header = [h.strip() for h in table[0]]
    lowered = [h.lower() for h in header]
    dupes = {h for h in lowered if h and lowered.count(h) > 1}
    if dupes:
        raise ValueError(f"ambiguous duplicate columns: {sorted(dupes)}")
    missing = [f for f in src["required_fields"] if f not in lowered]
    if missing:
        raise ValueError(f"missing required fields {missing}; renamed fields are not guessed")
    idx = {h: i for i, h in enumerate(lowered)}
    rows, problems = [], []
    seen: set[str] = set()
    for n, raw in enumerate(table[1:], start=2):
        if not any(c.strip() for c in raw):
            continue
        row = {f: (raw[idx[f]].strip() if idx[f] < len(raw) else "") for f in lowered if f}
        row["_row"] = n
        key = row.get(src["key_field"], "")
        if not key:
            problems.append(f"row {n}: blank {src['key_field']}")
            continue
        if key in seen:
            problems.append(f"row {n}: duplicate {src['key_field']} {key}")
            continue
        seen.add(key)
        rows.append(row)
    extra = [h for h in header if h.lower() not in src["required_fields"]]
    versions = sorted({r.get(src["version_field"], "") for r in rows} - {""}) if src.get("version_field") else []
    return {"header": header, "rows": rows, "problems": problems, "extra_columns": extra,
            "versions": versions}


def parse_notion(body: bytes) -> dict:
    data = json.loads(body.decode("utf-8"))
    blocks = data.get("recordMap", {}).get("block", {})

    def val(k):
        v = blocks[k].get("value", {})
        return v.get("value", v)

    roots = [k for k in blocks if val(k).get("type") == "page"]
    if not roots:
        raise ValueError("Notion response has no page block (login or landing page?)")
    root = roots[0]
    ordered = []

    def walk(k):
        v = val(k)
        title = v.get("properties", {}).get("title")
        if title and v.get("type") != "page":
            ordered.append({"block_id": k, "type": v.get("type"),
                            "text": "".join(x[0] for x in title)})
        for c in v.get("content", []) or []:
            if c in blocks:
                walk(c)

    walk(root)
    page_title = "".join(x[0] for x in val(root).get("properties", {}).get("title", []))
    edited = val(root).get("last_edited_time")
    return {"title": page_title, "blocks": ordered,
            "last_edited": dt.datetime.fromtimestamp(edited / 1000, dt.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ") if edited else None}


def html_version(src: dict, text: str, title: str, headers: dict) -> dict:
    meta = {"title": title, "last_modified_header": headers.get("Last-Modified"),
            "etag": headers.get("ETag")}
    oj = re.search(r"OJ L, (\d{4}/\d+), (\d{1,2}\.\d{1,2}\.\d{4})", text)
    if oj:
        meta["oj_reference"] = oj.group(1)
        meta["oj_publication_date"] = dt.datetime.strptime(oj.group(2), "%d.%m.%Y").date().isoformat()
    cons = re.search(r"02024R1689-(\d{8})", text)
    if cons and src["id"] == "SRC-LAW-CONS":
        meta["consolidation_date"] = dt.datetime.strptime(cons.group(1), "%Y%m%d").date().isoformat()
    sd = re.search(r"consolidated version of the AI Act as at (\d{1,2} \w+ \d{4})", text)
    if sd:
        meta["based_on_consolidation"] = dt.datetime.strptime(sd.group(1), "%d %B %Y").date().isoformat()
    return meta


# ---------------------------------------------------------------------------
# Legal extraction (stage 03 inputs).
# ---------------------------------------------------------------------------


def article_block(text: str, number: int) -> str | None:
    heads = [m.start() for m in re.finditer(rf"\n\s*Article {number}\s*\n", text)]
    if not heads:
        return None
    start = heads[-1]
    nxt = re.search(rf"\n\s*(Article {number + 1}\s*\n|CHAPTER [IVXL]+\s*\n)", text[start + 10:])
    return text[start: start + 10 + nxt.start()] if nxt else text[start: start + 20000]


def article_paragraphs(block: str, count: int) -> dict[str, str]:
    paras: dict[str, str] = {}
    positions = []
    pos = 0
    for n in range(1, count + 1):
        m = re.compile(rf"\n\s*{n}\.\s").search(block, pos)
        if not m:
            break
        positions.append((n, m.start()))
        pos = m.end()
    for i, (n, start) in enumerate(positions):
        end = positions[i + 1][1] if i + 1 < len(positions) else len(block)
        chunk = re.sub(rf"^\s*{n}\.\s*", "", block[start:end].strip())
        chunk = chunk.replace("▼M1", "").replace("▼B", "")
        paras[str(n)] = norm_space(chunk)
    return paras


# ---------------------------------------------------------------------------
# Run state
# ---------------------------------------------------------------------------


class Run:
    def __init__(self, args):
        self.args = args
        self.out: Path = args.out
        self.started = now_utc()
        self.run_id = "RUN-" + self.started.replace("-", "").replace(":", "")
        self.review_date = args.review_date
        self.snap_dir = self.out / "snapshots"
        self.src_dir = self.out / "sources" / self.run_id
        self.snapshots: list[dict] = []
        self.snapshot_paths: list[Path] = []
        self.evidence: dict[str, dict] = {}  # evidence id -> extract record
        self.sources: dict[str, dict] = {}   # source id -> final source record
        self.data: dict[str, dict] = {}      # source id -> parsed content
        self.failures: list[dict] = []
        self.history_note: dict = {}

    # -- evidence ---------------------------------------------------------
    def add_evidence(self, eid: str, source_id: str, locator: str, text: str) -> str:
        self.evidence[eid] = {"id": eid, "source_id": source_id, "locator": locator,
                              "extract": text, "summary": f"{source_id} {locator}",
                              "evidence_ids": [source_id]}
        return eid

    # -- snapshots --------------------------------------------------------
    def write_snapshot(self, stage: str, status: str, state: dict, consumed: list[str],
                       produced: list[str], unresolved: list[dict], decisions: list[dict],
                       extra: dict | None = None) -> None:
        seq = STAGES.index(stage) + 1
        pred = None
        if seq > 1:
            prev = self.snapshot_paths[-1]
            pred = {"snapshot_id": self.snapshots[-1]["snapshot_id"], "path": rel(prev),
                    "sha256": sha256_file(prev)}
        snap = {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": f"{self.run_id}-S{seq:02d}",
            "run_id": self.run_id,
            "stage": stage,
            "sequence": seq,
            "created_at": now_utc(),
            "status": status,
            "predecessor": pred,
            "consumed_record_ids": sorted(set(consumed)),
            "produced_record_ids": sorted(set(produced)),
            "state": state,
            "unresolved": unresolved,
            "decisions": decisions,
        }
        if extra:
            snap.update(extra)
        self.snap_dir.mkdir(parents=True, exist_ok=True)
        path = self.snap_dir / f"{seq:02d}-{stage}.json"
        path.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.snapshots.append(snap)
        self.snapshot_paths.append(path)


# ---------------------------------------------------------------------------
# History: keep the previous run before replacing outputs.
# ---------------------------------------------------------------------------


def archive_previous(out: Path) -> dict:
    first = out / "snapshots" / "01-scope.json"
    present = [p for p in [out / "snapshots", out / "sources"] + [out / f for f in FINAL_FILES.values()]
               if p.exists()]
    if not present:
        return {"supersedes_run_id": None, "archived_to": None, "archive_notes": []}
    old_id, notes = None, []
    try:
        old_id = json.loads(first.read_text(encoding="utf-8"))["run_id"]
    except Exception as e:  # missing or corrupt previous scope snapshot
        notes.append(f"previous 01-scope.json unreadable ({type(e).__name__}); archived as found")
        old_id = "UNKNOWN-" + now_utc().replace("-", "").replace(":", "")
    dest = out / "history" / old_id
    dest.mkdir(parents=True, exist_ok=True)
    for p in present:
        target = dest / p.name
        if target.exists():
            notes.append(f"{p.name} already archived for {old_id}; kept the earlier copy")
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            continue
        shutil.move(str(p), str(target))
    for f in FINAL_FILES.values():
        if not (dest / f).exists():
            notes.append(f"previous run had no {f}")
    return {"supersedes_run_id": old_id, "archived_to": rel(dest), "archive_notes": notes}


# ---------------------------------------------------------------------------
# Stage 01 — scope
# ---------------------------------------------------------------------------


def stage_scope(run: Run, scope_cfg: dict, hist: dict) -> None:
    decisions = [d for d in DECISIONS if d["stage"] == "scope"]
    state = {
        "as_of": f"{run.review_date}T00:00:00Z",
        "review_date": run.review_date,
        "review_date_note": "Assigned review date. Source retrieval times are recorded separately in stage 02.",
        "review_type": scope_cfg["review_type"],
        "systems_in_scope": scope_cfg["systems_in_scope"],
        "scope_basis": scope_cfg["scope_basis"],
        "audiences": scope_cfg["audiences"],
        "approval_gates": scope_cfg["approval_gates"],
        "out_of_scope_actions": scope_cfg["out_of_scope_actions"],
        "run_started_at": run.started,
        "supersedes_run_id": hist["supersedes_run_id"],
        "change_or_retry_reason": run.args.reason,
        "previous_run_archive": hist["archived_to"],
        "archive_notes": hist["archive_notes"],
    }
    ipath = REPO_DIR / scope_cfg["interview_file"]
    run.add_evidence("EV-INTERVIEW", "INTERVIEW", f"{scope_cfg['interview_file']} ({sha256_file(ipath)})",
                     "Work Sim interview export with the Compliance and Operations Manager; timestamps cited in decisions and config.")
    state["interview_record"] = {"path": scope_cfg["interview_file"], "sha256": sha256_file(ipath)}
    produced = ["SCOPE-" + run.run_id, "EV-INTERVIEW"]
    run.write_snapshot("scope", "complete", state, [], produced, [], decisions,
                       extra={"supersedes_run_id": hist["supersedes_run_id"]})


# ---------------------------------------------------------------------------
# Stage 02 — source capture
# ---------------------------------------------------------------------------


def capture_source(run: Run, src: dict, attempts: list[dict]) -> None:
    run.src_dir.mkdir(parents=True, exist_ok=True)
    final = None
    for attempt in range(1, run.args.retries + 2):
        rec = {
            "id": f"{src['id']}#A{attempt}", "source_id": src["id"],
            "summary": f"Attempt {attempt} to read {src['label']}",
            "evidence_ids": [], "source_role": src["source_role"], "authority": src["authority"],
            "locator": src["url"], "retrieved_at": now_utc(), "retrieval_status": "unavailable",
            "content_type": "unknown", "version_metadata": None, "content_hash": None,
            "local_reference": None, "required": src["required"], "interview_ref": src.get("interview_ref"),
            "used_in_deliverables": False, "reason": None, "owner": "Compliance and Operations Manager",
        }
        try:
            body, ctype, eff, headers = fetch_once(src)
            rec["retrieved_at"] = now_utc()
            rec["content_type"] = ctype or "unknown"
            rec["effective_locator"] = eff
            ext = {"html": "html", "sheet": "csv", "notion": "json"}[src["kind"]]
            path = run.src_dir / f"{src['id']}.{ext}"
            path.write_bytes(body)
            rec["content_hash"] = sha256_bytes(body)
            rec["local_reference"] = rel(path)
            parsed, status, reason = verify_source(src, body, ctype, headers, run.review_date)
            rec["retrieval_status"] = status
            rec["reason"] = reason
            rec["version_metadata"] = parsed.get("version") if parsed else None
            if status == "retrieved":
                run.data[src["id"]] = parsed
                rec["summary"] = f"{src['label']} retrieved and identity verified"
                final = rec
                attempts.append(rec)
                break
        except (urllib.error.URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError, SourceUnavailable) as e:
            rec["reason"] = f"{type(e).__name__}: {e}"
            rec["summary"] = f"{src['label']} could not be read: {rec['reason']}"
        attempts.append(rec)
        if attempt <= run.args.retries:
            time.sleep(run.args.retry_wait * attempt)  # polite backoff; challenges are not retried rapidly
    if final is None:
        last = attempts[-1]
        run.failures.append({"stage": "source-capture", "source_id": src["id"], "reason": last["reason"],
                             "recovery": "Re-run the documented command; if it persists, report the "
                                         "unavailable route to the source owner / facilitator."})
        final = last
    run.sources[src["id"]] = final


def verify_source(src: dict, body: bytes, ctype: str, headers: dict, review_date: str):
    """Return (parsed, status, reason). Identity and suitability for the review date."""
    if src["kind"] == "sheet":
        if "text/csv" not in ctype:
            return None, "invalid", f"expected CSV, got {ctype!r} (sign-in or error page?)"
        try:
            parsed = parse_sheet(body, src)
        except ValueError as e:
            return None, "invalid", str(e)
        parsed["version"] = {"record_versions": parsed["versions"], "rows": len(parsed["rows"]),
                             "header": parsed["header"], "extra_columns": parsed["extra_columns"],
                             "row_problems": parsed["problems"]}
        late = [v for v in parsed["versions"] if re.search(r"(\d{4}-\d{2}-\d{2})", v)
                and re.search(r"(\d{4}-\d{2}-\d{2})", v).group(1) > review_date]
        if late:
            parsed["version"]["note"] = f"version label(s) {late} later than review date; recorded, not used to move the review date"
        return parsed, "retrieved", None
    if src["kind"] == "notion":
        if "json" not in ctype:
            return None, "invalid", f"expected JSON from the public page API, got {ctype!r}"
        parsed = parse_notion(body)
        full = "\n".join(b["text"] for b in parsed["blocks"])
        missing = [m for m in src["identity_markers"] if m not in full]
        if missing:
            return None, "invalid", f"identity markers not found: {missing}"
        pol = re.search(r"Policy version:\s*(\S+)", full)
        ctx = re.search(r"Context revision:\s*(\S+)", full)
        parsed["version"] = {"page_title": parsed["title"], "policy_version": pol.group(1) if pol else None,
                             "context_revision": ctx.group(1) if ctx else None,
                             "page_last_edited": parsed["last_edited"]}
        return parsed, "retrieved", None
    # html
    if "html" not in ctype:
        return None, "invalid", f"expected HTML, got {ctype!r}"
    text, title = html_to_text(body)
    missing = [m for m in src["identity_markers"] if m.lower() not in text.lower()]
    if missing:
        return None, "invalid", f"identity markers not found (landing/login page?): {missing}"
    version = html_version(src, text, title, headers)
    parsed = {"text": text, "title": title, "version": version}
    if src["id"] == "SRC-LAW-CONS" and version.get("consolidation_date", "9999") > review_date:
        return parsed, "invalid", "consolidation later than the review date"
    if src["id"] == "SRC-LAW-AMEND" and version.get("oj_publication_date", "9999") > review_date:
        return parsed, "invalid", "amendment published after the review date"
    return parsed, "retrieved", None


def stage_capture(run: Run, sources_cfg: list[dict]) -> list[dict]:
    attempts: list[dict] = []
    for src in sources_cfg:
        capture_source(run, src, attempts)
    # Evidence extracts with locators, written next to the captured bytes.
    build_row_evidence(run)
    produced = [a["id"] for a in attempts] + list(run.evidence)
    for a in attempts:
        a["evidence_ids"] = [e for e, v in run.evidence.items() if v["source_id"] == a["source_id"]] \
            if a["retrieval_status"] == "retrieved" else []
    failed_required = [s for s in sources_cfg if s["required"]
                       and run.sources[s["id"]]["retrieval_status"] != "retrieved"]
    failed_any = [s for s in sources_cfg if run.sources[s["id"]]["retrieval_status"] != "retrieved"]
    status = "blocked" if failed_required else ("partial" if failed_any else "complete")
    unresolved = [{"id": f"UNR-SRC-{s['id']}", "summary": f"{s['label']} not usable this run",
                   "evidence_ids": [run.sources[s['id']]["id"]], "owner": "Compliance and Operations Manager",
                   "reason": run.sources[s["id"]]["reason"],
                   "resolution_need": "Restore access to the disclosed route and re-run; no undisclosed local copy is substituted."}
                  for s in failed_any]
    state = {"review_date": run.review_date, "sources": attempts,
             "evidence_extract_file": rel(run.src_dir / "extracts.json")}
    write_extracts(run)
    run.write_snapshot("source-capture", status, state, [run.snapshots[0]["produced_record_ids"][0]],
                       produced, unresolved, [d for d in DECISIONS if d["stage"] == "source-capture"])
    return attempts


def build_row_evidence(run: Run) -> None:
    for sid, key in (("SRC-SYSTEMS", "system_id"), ("SRC-EVIDENCE", "record_id"), ("SRC-CALENDAR", "action_id")):
        d = run.data.get(sid)
        if not d:
            continue
        tab = sid.split("-")[1]
        for r in d["rows"]:
            fields = {k: v for k, v in r.items() if not k.startswith("_")}
            run.add_evidence(ev_id(tab, r[key]), sid, f"{tab} sheet row {r['_row']} ({key}={r[key]})",
                             json.dumps(fields, ensure_ascii=False))
    pol = run.data.get("SRC-POLICY")
    if pol:
        section, sub = "", ""
        for b in pol["blocks"]:
            if b["type"] in ("header", "sub_header"):
                section, sub = b["text"], ""
            elif b["type"] == "sub_sub_header":
                sub = b["text"]
            run.data["SRC-POLICY"].setdefault("located", []).append(
                {**b, "section": section, "subsection": sub})


def write_extracts(run: Run) -> None:
    run.src_dir.mkdir(parents=True, exist_ok=True)
    (run.src_dir / "extracts.json").write_text(
        json.dumps({"run_id": run.run_id, "extracts": list(run.evidence.values())}, indent=2,
                   ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Stage 03 — authority and timing
# ---------------------------------------------------------------------------


def stage_authority(run: Run) -> dict:
    binding, timing, guidance, blockers = [], [], [], []
    para_text: dict[str, str] = {}
    oj = run.data.get("SRC-LAW-OJ")
    amend = run.data.get("SRC-LAW-AMEND")
    cons = run.data.get("SRC-LAW-CONS")
    sd = run.data.get("SRC-ART50-SD")

    if oj:
        block = article_block(oj["text"], 50)
        paras = article_paragraphs(block or "", 7)
        if len(paras) < 6:
            blockers.append({"id": "BLK-OJ-ART50", "summary": "Article 50 paragraphs not found in the OJ text",
                             "evidence_ids": [run.sources["SRC-LAW-OJ"]["id"]], "owner": "Legal",
                             "rationale": "Binding text could not be located in the retrieved document."})
        for n, t in paras.items():
            eid = run.add_evidence(ev_id("OJ", "ART50", n), "SRC-LAW-OJ", f"Regulation (EU) 2024/1689, Article 50({n})", t)
            para_text[n] = t
            if n == "7":
                continue  # replaced by the amendment below
            binding.append({"id": f"RULE-ART50-{n}", "summary": t[:300], "evidence_ids": [eid],
                            "rule_ref": f"EU AI Act Art. 50({n})", "authority": "binding", "owner": "Legal",
                            "addressee": "provider" if t.startswith("Providers") else
                                         ("deployer" if t.startswith("Deployers") else "all")})
        a113 = article_block(oj["text"], 113) or ""
        if "It shall apply from 2 August 2026" in norm_space(a113):
            eid = run.add_evidence(ev_id("OJ", "ART113"), "SRC-LAW-OJ", "Regulation (EU) 2024/1689, Article 113, second paragraph",
                                   "It shall apply from 2 August 2026.")
            timing.append({"id": "TIME-ART50-APPLIES", "summary": "Article 50 applies from 2 August 2026 (general date of application, Art. 113); it is in force for the 26 August 2026 review.",
                           "evidence_ids": [eid], "effective_date": "2026-08-02", "owner": "Legal"})
    else:
        blockers.append({"id": "BLK-OJ", "summary": "Binding Regulation (EU) 2024/1689 text unavailable this run",
                         "evidence_ids": [run.sources["SRC-LAW-OJ"]["id"]], "owner": "Legal",
                         "rationale": run.sources["SRC-LAW-OJ"]["reason"]})

    if amend:
        t = amend["text"]
        nt = norm_space(t)
        m7 = re.search(r"in Article 50, paragraph 7 is replaced by the following:\s*‘?7\.\s*(.+?)’", nt)
        m111 = re.search(r"‘4\. (Providers of AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content, that have been placed on the market before 2 August 2026 shall take the necessary steps in order to comply with Article 50\(2\) by 2 December 2026\.)’", nt)
        efor = re.search(r"enter into force [^.]*?on the (third|twentieth) day following that of its publication", nt)
        v = run.sources["SRC-LAW-AMEND"]["version_metadata"] or {}
        if m7:
            eid = run.add_evidence(ev_id("AMEND", "ART50", "7"), "SRC-LAW-AMEND", "Regulation (EU) 2026/1744, amendment replacing Article 50(7)", m7.group(1))
            binding.append({"id": "RULE-ART50-7", "summary": "Art. 50(7) as replaced by Regulation (EU) 2026/1744: codes of practice for detection, marking and labelling; Commission may adopt implementing act if inadequate.",
                            "evidence_ids": [eid], "rule_ref": "EU AI Act Art. 50(7) (as amended)", "authority": "binding",
                            "owner": "Legal", "addressee": "Commission"})
        if m111:
            eid = run.add_evidence(ev_id("AMEND", "ART111", "4"), "SRC-LAW-AMEND", "Regulation (EU) 2026/1744, new Article 111(4) of Regulation (EU) 2024/1689", m111.group(1))
            timing.append({"id": "TIME-ART50-2-TRANSITION", "summary": "Providers of generative systems placed on the market before 2 August 2026 must comply with Art. 50(2) by 2 December 2026. This is a provider-side transition; it does not move Quillhaven's deployer duties.",
                           "evidence_ids": [eid], "effective_date": "2026-12-02", "owner": "Legal"})
        if efor and v.get("oj_publication_date"):
            days = 3 if efor.group(1) == "third" else 20
            pub = dt.date.fromisoformat(v["oj_publication_date"])
            eif = (pub + dt.timedelta(days=days)).isoformat()
            eid = run.add_evidence(ev_id("AMEND", "ENTRYINTOFORCE"), "SRC-LAW-AMEND", "Regulation (EU) 2026/1744, recital on entry into force; OJ reference",
                                   f"{efor.group(0)}; published OJ L {v.get('oj_reference')} on {v['oj_publication_date']}")
            timing.append({"id": "TIME-AMEND-IN-FORCE", "summary": f"Regulation (EU) 2026/1744 published {v['oj_publication_date']}, in force {eif} ({efor.group(1)} day after publication); effective before the {run.review_date} review date.",
                           "evidence_ids": [eid], "effective_date": eif, "owner": "Legal"})
        if not (m7 and m111):
            blockers.append({"id": "BLK-AMEND-PARSE", "summary": "Amendment retrieved but the Article 50 changes could not be located",
                             "evidence_ids": [run.sources["SRC-LAW-AMEND"]["id"]], "owner": "Legal",
                             "rationale": "Amendment content must be confirmed before formal conclusions."})
    else:
        blockers.append({"id": "BLK-AMEND", "summary": "Amending Regulation (EU) 2026/1744 unavailable this run",
                         "evidence_ids": [run.sources["SRC-LAW-AMEND"]["id"]], "owner": "Legal",
                         "rationale": run.sources["SRC-LAW-AMEND"]["reason"]})

    # Navigation aids and official guidance: cross-checks and context, never the binding basis.
    if cons:
        block = article_block(cons["text"], 50)
        cparas = article_paragraphs(block or "", 7)
        same = [n for n in ("1", "2", "3", "4", "5", "6") if norm_space(cparas.get(n, ""))[:200] == norm_space(para_text.get(n, ""))[:200]]
        eid = run.add_evidence(ev_id("CONS", "ART50"), "SRC-LAW-CONS", "Consolidated text 02024R1689-20260727, Article 50",
                               f"Paragraphs matching the OJ text: {same}; consolidated 50(7) present: {'7' in cparas}")
        guidance.append({"id": "CTX-CONSOLIDATED", "summary": f"27 July 2026 consolidation used only as a navigation aid; Art. 50(1)-(6) match the OJ text for paragraphs {', '.join(same) or 'none'}.",
                         "evidence_ids": [eid], "owner": "Legal", "authority": "advisory"})
    if sd:
        sparas = article_paragraphs("\n" + sd["text"].split("The text displayed here is based on", 1)[-1], 7)
        eid = run.add_evidence(ev_id("SD", "ART50"), "SRC-ART50-SD", "AI Act Service Desk Article 50 page",
                               f"Service Desk reproduction based on consolidation {(run.sources['SRC-ART50-SD']['version_metadata'] or {}).get('based_on_consolidation')}; paragraphs found: {sorted(sparas)}")
        guidance.append({"id": "CTX-SERVICE-DESK", "summary": "Service Desk Article 50 page is a reproduction of the consolidated text, used for cross-checking only.",
                         "evidence_ids": [eid], "owner": "Legal", "authority": "advisory"})
    tl = run.data.get("SRC-TIMELINE")
    if tl:
        t = norm_space(tl["text"])
        if "Transparency rules (Article 50) start to apply" in t:
            eid = run.add_evidence(ev_id("TIMELINE", "20260802"), "SRC-TIMELINE", "Timeline entry 02 Aug 2026", "Transparency rules (Article 50) start to apply.")
            guidance.append({"id": "CTX-TIMELINE-0802", "summary": "Official timeline: Article 50 transparency rules apply from 2 August 2026 (consistent with Art. 113).",
                             "evidence_ids": [eid], "owner": "Legal", "authority": "advisory"})
        m = re.search(r"Transitional deadline for certain providers[^.]*Article 50\(2\)\.", t)
        if m:
            eid = run.add_evidence(ev_id("TIMELINE", "20261202"), "SRC-TIMELINE", "Timeline entry 02 Dec 2026", m.group(0))
            guidance.append({"id": "CTX-TIMELINE-1202", "summary": "Official timeline: 2 December 2026 transitional deadline for certain providers under Art. 50(2) (consistent with new Art. 111(4)).",
                             "evidence_ids": [eid], "owner": "Legal", "authority": "advisory"})
    g = run.data.get("SRC-GUIDANCE")
    if g:
        t = norm_space(g["text"])
        m = re.search(r"Under the AI Act, deployers must ensure that they inform people[^.]*\.", t)
        if m:
            eid = run.add_evidence(ev_id("GUIDANCE", "DEPLOYERS"), "SRC-GUIDANCE", "Commission Article 50 FAQ, deployer obligations", m.group(0))
            guidance.append({"id": "CTX-GUIDANCE-DEPLOYER", "summary": "Commission FAQ summarises deployer duties as Art. 50(3) information and Art. 50(4) deep-fake / public-interest text disclosure; explanatory, not binding.",
                             "evidence_ids": [eid], "owner": "Legal", "authority": "advisory"})

    authority_ok = not any(b["id"] in ("BLK-OJ", "BLK-OJ-ART50", "BLK-AMEND", "BLK-AMEND-PARSE") for b in blockers)
    status = "complete" if authority_ok else "blocked"
    consumed = [run.sources[s]["id"] for s in ("SRC-LAW-OJ", "SRC-LAW-AMEND", "SRC-LAW-CONS", "SRC-ART50-SD", "SRC-TIMELINE", "SRC-GUIDANCE")
                if s in run.sources and run.sources[s]["retrieval_status"] == "retrieved"] or [run.sources["SRC-LAW-OJ"]["id"]]
    state = {"review_date": run.review_date, "binding_rules": binding, "timing_rules": timing,
             "guidance_context": guidance, "authority_blockers": blockers,
             "authority_available": authority_ok,
             "legal_version_basis": "Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744 (in force before the review date); the 27 July 2026 consolidation is a navigation aid, not a separate act."}
    produced = [r["id"] for r in binding + timing + guidance + blockers]
    write_extracts(run)
    run.write_snapshot("authority-and-timing", status, state, consumed, produced, list(blockers),
                       [d for d in DECISIONS if d["stage"] == "authority-and-timing"])
    return {"authority_ok": authority_ok, "binding": {r["id"]: r for r in binding}}


# ---------------------------------------------------------------------------
# Stage 04 — evidence reconciliation
# ---------------------------------------------------------------------------

# Field meanings disclosed in the interview (03:35 PM) and the policy. Values outside these sets are
# reported, never guessed.
NOTICE_VALUES = {"yes", "no", "unknown", "visible_label", "not_applicable"}
ROLE_VALUES = {"yes", "no", "unknown"}
EVIDENCE_STATUS = {"complete", "partial", "missing", "stale", "conflicting", "not_applicable"}

# Policy clauses are located by meaning, not position.
POLICY_CONTROLS = [
    ("CTRL-NOTICE", r"directly interacting with an AI system must receive a clear notice"),
    ("CTRL-SYNTHETIC", r"synthetic images, audio, or video must retain machine-readable provenance"),
    ("CTRL-STAFF-DRAFT", r"Staff-only drafting tools are not automatically treated as public"),
    ("CTRL-REGISTER", r"Each registered system must have a current owner"),
    ("CTRL-EVIDENCE-STATES", r"missing, stale, conflicting, and not-applicable are different evidence states"),
    ("CTRL-EXCEPTION", r"An exception requires a named owner, rationale, expiry date, and Legal approval"),
    ("CTRL-BOUNDARY", r"may not give final legal advice"),
]

# Operating facts (policy context, per system). Each matcher records the sentence it relied on.
FACT_MATCHERS = {
    "biometric_or_emotion": [
        (r"does not classify biometric data or infer emotions", "no"),
        (r"not used to identify or infer emotions", "no"),
        (r"not yet established whether the flagging uses biometric data", "unknown"),
    ],
    "deep_fake": [
        (r"real people; the altered recording makes them appear", "yes"),
        (r"not depictions of an existing person", "no"),
    ],
    "artistic_or_fictional_work": [
        (r"not an evidently artistic, satirical or fictional", "no"),
    ],
    "public_interest_text": [
        (r"not material published to inform the public", "no"),
        (r"not published or sent to applicants, learners or the general public", "no"),
    ],
    "direct_interaction": [
        (r"exchange questions and generated replies directly", "yes"),
        (r"interact directly with the licensed", "yes"),
        (r"converse directly with the licensed", "yes"),
        (r"applicants do not converse with the AI product", "no"),
    ],
}


def policy_sentence(text: str, pattern: str) -> str:
    for s in re.split(r"(?<=[.;])\s+", text):
        if re.search(pattern, s, re.I):
            return s.strip()
    return text


def stage_evidence(run: Run, scope_cfg: dict) -> dict:
    systems = run.data.get("SRC-SYSTEMS")
    records = run.data.get("SRC-EVIDENCE")
    calendar = run.data.get("SRC-CALENDAR")
    policy = run.data.get("SRC-POLICY")
    system_facts, policy_controls, incident_evidence, conflicts, gaps = [], [], [], [], []
    facts: dict[str, dict] = {}

    # Policy controls
    located = policy.get("located", []) if policy else []
    pol_ver = (run.sources["SRC-POLICY"]["version_metadata"] or {}).get("policy_version") if policy else None
    controls: dict[str, dict] = {}
    for cid, pat in POLICY_CONTROLS:
        hit = next((b for b in located if re.search(pat, b["text"], re.I)), None)
        if hit:
            eid = run.add_evidence(ev_id("POLICY", cid), "SRC-POLICY",
                                   f"{pol_ver} > {hit['section']} (block {hit['block_id']})", hit["text"])
            rec = {"id": cid, "summary": hit["text"], "evidence_ids": [eid], "owner": "Operations",
                   "rule_ref": f"{pol_ver}: {hit['section']}", "policy_version": pol_ver}
            controls[cid] = rec
            policy_controls.append(rec)
        else:
            gaps.append({"id": f"GAP-{cid}", "summary": f"Policy clause {cid} not found in the retrieved policy",
                         "evidence_ids": [run.sources["SRC-POLICY"]["id"]], "owner": "Operations",
                         "resolution_need": "Operations confirms the current policy wording."})

    # Operating-scope paragraph: who is the provider
    scope_para = next((b for b in located if "licenses and operates a third-party supplier" in b["text"]), None)
    deployer_only: set[str] = set()
    if scope_para:
        first = scope_para["text"].split("It did not develop", 1)[0]
        deployer_only = set(re.findall(r"AI-\d{3}", first))
        run.add_evidence(ev_id("POLICY", "OPERATINGSCOPE"), "SRC-POLICY",
                         f"{pol_ver} context > Operating scope (block {scope_para['block_id']})", scope_para["text"])
    timing_para = next((b for b in located if "first offered commercially in the EU" in b["text"]), None)
    if timing_para:
        run.add_evidence(ev_id("POLICY", "PRODUCTTIMING"), "SRC-POLICY",
                         f"context > Product timing and evidence limits (block {timing_para['block_id']})", timing_para["text"])

    # Evidence records by system
    by_system: dict[str, list[dict]] = {}
    if records:
        for r in records["rows"]:
            by_system.setdefault(r["system_id"], []).append(r)
            eid = ev_id("EVIDENCE", r["record_id"])
            incident_evidence.append({"id": r["record_id"], "summary": f"{r['record_type']} for {r['system_id']}: {r['notes']}",
                                      "evidence_ids": [eid], "owner": r["owner"], "system_id": r["system_id"],
                                      "record_type": r["record_type"], "status": r["status"],
                                      "evidence_state": r["evidence_state"], "reported_at": r["reported_at"],
                                      "evidence_ref": r["evidence_ref"]})
            if r["reported_at"] > run.review_date:
                gaps.append({"id": f"GAP-LATE-{r['record_id']}", "summary": f"{r['record_id']} reported after the review date",
                             "evidence_ids": [eid], "owner": r["owner"], "resolution_need": "Excluded from the as-of position; Legal/Operations decide whether to re-scope."})

    actions_by_system: dict[str, list[dict]] = {}
    if calendar:
        for a in calendar["rows"]:
            actions_by_system.setdefault(a["system_id"], []).append(a)

    if systems:
        reg_ids = [r["system_id"] for r in systems["rows"]]
        for sid in scope_cfg["systems_in_scope"]:
            if sid not in reg_ids:
                gaps.append({"id": f"GAP-SCOPE-{sid}", "summary": f"{sid} in scope but absent from SYSTEMS",
                             "evidence_ids": [run.sources["SRC-SYSTEMS"]["id"]], "owner": "Operations",
                             "resolution_need": "Register owner restores the row or confirms retirement."})
        for r in systems["rows"]:
            sid = r["system_id"]
            sys_eid = ev_id("SYSTEMS", sid)
            f = {k: v for k, v in r.items() if not k.startswith("_")}
            problems = []
            for fld, allowed in (("current_notice", NOTICE_VALUES), ("provider_role", ROLE_VALUES),
                                 ("deployer_role", ROLE_VALUES), ("evidence_status", EVIDENCE_STATUS)):
                if f.get(fld, "") not in allowed:
                    problems.append(f"{fld}={f.get(fld)!r} is not a disclosed value")
            try:
                dt.date.fromisoformat(f.get("evidence_updated_at", ""))
            except ValueError:
                problems.append(f"evidence_updated_at={f.get('evidence_updated_at')!r} is not a date")
            # Policy operating facts for this system
            sect = [b for b in located if b.get("subsection") == sid and b["type"] == "text"]
            ftext = " ".join(b["text"] for b in sect)
            fact_eids = [sys_eid]
            if sect:
                fact_eids.append(run.add_evidence(ev_id("POLICY", sid), "SRC-POLICY",
                                                  f"context > Actual use and content > {sid} (block {sect[0]['block_id']})", ftext))
            derived = {}
            for fact, matchers in FACT_MATCHERS.items():
                derived[fact] = {"value": "not-stated", "basis": None}
                for pat, value in matchers:
                    if re.search(pat, ftext, re.I):
                        derived[fact] = {"value": value, "basis": policy_sentence(ftext, pat)}
                        break
            # Corroborate register direct-interaction with the operating facts
            if f.get("output_type") == "direct_interaction" and derived["direct_interaction"]["value"] == "not-stated":
                derived["direct_interaction"] = {"value": "yes", "basis": "SYSTEMS output_type=direct_interaction"}
            role_note = None
            if sid in deployer_only and f.get("provider_role") == "no":
                role = "deployer-only"
                role_note = "Register provider_role=no corroborated by the policy operating-scope paragraph (licensed supplier product)."
                fact_eids.append(ev_id("POLICY", "OPERATINGSCOPE"))
            elif f.get("provider_role") == "unknown" or (f.get("provider_role") == "no" and scope_para and sid not in deployer_only):
                role = "unknown"
                role_note = "Provider role not established: register and/or policy record it as unresolved."
                if scope_para:
                    fact_eids.append(ev_id("POLICY", "OPERATINGSCOPE"))
            elif f.get("provider_role") == "yes":
                role = "provider"
            else:
                role = "deployer-only" if f.get("provider_role") == "no" else "unknown"
            recs = by_system.get(sid, [])
            open_states = sorted({x["evidence_state"] for x in recs if x["status"] != "closed"})
            facts[sid] = {"row": f, "role": role, "derived": derived, "records": recs,
                          "open_states": open_states, "evidence_ids": fact_eids, "problems": problems,
                          "actions": actions_by_system.get(sid, [])}
            system_facts.append({"id": f"FACT-{sid}", "summary": f"{sid} {f.get('system_name')}: {f.get('use_case')}; role {role}; notice {f.get('current_notice')}; evidence {f.get('evidence_status')} ({f.get('evidence_updated_at')})",
                                 "evidence_ids": fact_eids, "owner": f.get("owner"), "system_id": sid,
                                 "register_fields": f, "actor_role": role, "role_note": role_note,
                                 "derived_facts": derived, "field_problems": problems,
                                 "record_version": f.get("record_version")})
            if problems:
                gaps.append({"id": f"GAP-FIELDS-{sid}", "summary": "; ".join(problems), "evidence_ids": [sys_eid],
                             "owner": f.get("owner"), "resolution_need": "Register owner corrects the value; meanings are not guessed."})
            if f.get("evidence_status") == "stale" or "stale" in open_states:
                gaps.append({"id": f"GAP-STALE-{sid}", "summary": f"{sid} evidence is stale (last updated {f.get('evidence_updated_at')})",
                             "evidence_ids": [sys_eid] + [ev_id("EVIDENCE", x["record_id"]) for x in recs if x["evidence_state"] == "stale"],
                             "owner": f.get("owner"), "resolution_need": "Owner refreshes the evidence for the current release."})
            if "missing" in open_states:
                gaps.append({"id": f"GAP-MISSING-{sid}", "summary": f"{sid} has missing evidence: " + "; ".join(x["notes"] for x in recs if x["evidence_state"] == "missing"),
                             "evidence_ids": [ev_id("EVIDENCE", x["record_id"]) for x in recs if x["evidence_state"] == "missing"],
                             "owner": f.get("owner"), "resolution_need": "Owner supplies the evidence; missing is not treated as compliance or non-compliance."})
            if "conflicting" in open_states or f.get("evidence_status") == "conflicting":
                conflicts.append({"id": f"CONFLICT-{sid}", "summary": f"{sid} evidence conflicts: " + "; ".join(x["notes"] for x in recs if x["evidence_state"] == "conflicting"),
                                  "evidence_ids": [sys_eid] + [ev_id("EVIDENCE", x["record_id"]) for x in recs if x["evidence_state"] == "conflicting"],
                                  "owner": f.get("owner"), "resolution_need": "System owner resolves which account is current; both are preserved."})
    else:
        gaps.append({"id": "GAP-SYSTEMS", "summary": "SYSTEMS register unavailable; no system can be assessed this run",
                     "evidence_ids": [run.sources["SRC-SYSTEMS"]["id"]], "owner": "Operations",
                     "resolution_need": "Restore register access and re-run."})

    status = "complete" if systems and records and policy else ("blocked" if not systems else "partial")
    consumed = [r["id"] for r in run.snapshots[2]["state"]["binding_rules"]][:1] + \
               [run.sources[s]["id"] for s in ("SRC-SYSTEMS", "SRC-EVIDENCE", "SRC-CALENDAR", "SRC-POLICY")
                if run.sources[s]["retrieval_status"] == "retrieved"]
    if not consumed:
        consumed = [run.snapshots[1]["produced_record_ids"][0]]
    state = {"system_facts": system_facts, "policy_controls": policy_controls,
             "incident_evidence": incident_evidence, "conflicts": conflicts, "evidence_gaps": gaps,
             "field_meanings": FIELD_MEANINGS}
    produced = [r["id"] for r in system_facts + policy_controls + incident_evidence + conflicts + gaps]
    write_extracts(run)
    run.write_snapshot("evidence-reconciliation", status, state, consumed, produced, conflicts + gaps,
                       [d for d in DECISIONS if d["stage"] == "evidence-reconciliation"])
    return {"facts": facts, "controls": controls}


FIELD_MEANINGS = {
    "current_notice": "yes = notice in place; no = no notice; unknown = not established; visible_label = visible label only (does not prove machine-readable provenance, per interview 03:35 PM); not_applicable = no disclosure obligation identified by the owner",
    "provider_role / deployer_role": "yes / no / unknown as recorded by the register owner; unknown stays unresolved",
    "evidence_status / evidence_state": "complete, partial, missing, stale, conflicting, not_applicable are distinct states (policy CTRL-EVIDENCE-STATES); missing is never converted to compliance or non-compliance",
    "approval_required (CALENDAR)": "legal or operations: the role whose decision the action needs",
}


# ---------------------------------------------------------------------------
# Stage 05 — impact analysis
# ---------------------------------------------------------------------------


def statutory_assessment(sid: str, fx: dict, authority_ok: bool, binding: dict) -> dict:
    """Article 50 assessment for Quillhaven's own role. Returns state/rule/reason/need."""
    d = fx["derived"]
    row = fx["row"]
    out_type = row.get("output_type", "")
    ev = list(fx["evidence_ids"])
    if not authority_ok:
        return {"state": "unresolved", "rule_ref": "EU AI Act Art. 50", "evidence": ev,
                "reason": "Binding legal authority was unavailable or unsuitable this run; formal Article 50 conclusion withheld.",
                "need": "Re-run with the binding OJ and amendment texts retrieved.", "owner": "Legal"}

    def rule_ev(*ids):
        return [binding[i]["evidence_ids"][0] for i in ids if i in binding]

    if fx["role"] == "unknown":
        bio = d["biometric_or_emotion"]["value"]
        return {"state": "unresolved", "rule_ref": "EU AI Act Art. 50(1)-(3)",
                "evidence": ev + rule_ev("RULE-ART50-1", "RULE-ART50-2", "RULE-ART50-3"),
                "reason": f"Provider role is {row.get('provider_role')!r} in the register and current-release development/branding records are outstanding; "
                          f"whether the system uses biometric data to infer emotions or categories is '{bio}'. Provider duties under 50(1)-(2) and deployer duty under 50(3) cannot be settled.",
                "need": "Owner supplies current development, release and data-use records; Legal then decides role and Art. 50(3) applicability.",
                "owner": row.get("owner")}
    if fx["role"] == "provider":
        return {"state": "unresolved", "rule_ref": "EU AI Act Art. 50(1)-(2)", "evidence": ev + rule_ev("RULE-ART50-1", "RULE-ART50-2"),
                "reason": "Quillhaven recorded as provider; provider obligations need provider-side evidence not in the registers.",
                "need": "Legal confirms provider status and required evidence.", "owner": "Legal"}
    # deployer-only
    if d["biometric_or_emotion"]["value"] == "unknown":
        return {"state": "unresolved", "rule_ref": "EU AI Act Art. 50(3)", "evidence": ev + rule_ev("RULE-ART50-3"),
                "reason": "Whether the system performs emotion recognition or biometric categorisation is not established.",
                "need": "Owner supplies data-use facts; Legal decides.", "owner": row.get("owner")}
    if d["biometric_or_emotion"]["value"] == "yes":
        return {"state": "supported-impact", "rule_ref": "EU AI Act Art. 50(3)", "evidence": ev + rule_ev("RULE-ART50-3", "RULE-ART50-5"),
                "reason": "Deployer of an emotion-recognition / biometric-categorisation system must inform exposed persons.",
                "need": None, "owner": "Legal"}
    if out_type.startswith("synthetic_") and d["deep_fake"]["value"] == "yes":
        artistic = d["artistic_or_fictional_work"]["value"]
        limited = " The evidently artistic/fictional limitation does not apply (operating facts)." if artistic == "no" else ""
        return {"state": "supported-impact", "rule_ref": "EU AI Act Art. 50(4) first subparagraph; Art. 50(5)",
                "evidence": ev + rule_ev("RULE-ART50-4", "RULE-ART50-5"),
                "reason": "Quillhaven deploys a product that alters recordings of real presenters so they appear to say words they did not record, which a viewer could take as authentic: a deep fake. "
                          "As deployer it must disclose the artificial generation clearly at first exposure." + limited +
                          " Machine-readable marking under 50(2) is the supplier's (provider's) duty.",
                "need": "Legal confirms the interpretation and whether the recorded visible label meets 50(4)-(5) for every published video.",
                "owner": "Legal"}
    if out_type.startswith("synthetic_") and d["deep_fake"]["value"] == "no":
        return {"state": "supported-no-impact", "rule_ref": "EU AI Act Art. 50(4) first subparagraph",
                "evidence": ev + rule_ev("RULE-ART50-2", "RULE-ART50-4"),
                "reason": "Images are visibly illustrated fictional scenes, not depictions of existing persons, places or events presented as authentic, so the deployer deep-fake disclosure duty is not triggered. Art. 50(2) marking is the supplier's duty as provider.",
                "need": None, "owner": "Legal"}
    if out_type.startswith("synthetic_"):
        return {"state": "unresolved", "rule_ref": "EU AI Act Art. 50(4)", "evidence": ev + rule_ev("RULE-ART50-4"),
                "reason": "Synthetic media without operating facts on whether it resembles real persons or events.",
                "need": "Owner describes the published content; Legal decides.", "owner": row.get("owner")}
    if out_type == "text":
        pit = d["public_interest_text"]["value"]
        if pit == "no":
            return {"state": "supported-no-impact", "rule_ref": "EU AI Act Art. 50(4) second subparagraph",
                    "evidence": ev + rule_ev("RULE-ART50-4"),
                    "reason": "Generated text is not published to inform the public on matters of public interest (operating facts), so the deployer text-disclosure duty is not triggered.",
                    "need": None, "owner": "Legal"}
        return {"state": "unresolved", "rule_ref": "EU AI Act Art. 50(4) second subparagraph", "evidence": ev + rule_ev("RULE-ART50-4"),
                "reason": "Not established whether generated text is published to inform the public.",
                "need": "Owner describes publication; Legal decides.", "owner": row.get("owner")}
    if d["direct_interaction"]["value"] == "yes":
        return {"state": "supported-no-impact", "rule_ref": "EU AI Act Art. 50(1)",
                "evidence": ev + rule_ev("RULE-ART50-1", "RULE-ART50-3"),
                "reason": "Art. 50(1) is a provider design obligation; Quillhaven deploys a licensed supplier product and is not its provider. No emotion recognition or biometric categorisation (Art. 50(3)) per operating facts. The internal-policy notice requirement is assessed separately.",
                "need": None, "owner": "Legal"}
    return {"state": "unresolved", "rule_ref": "EU AI Act Art. 50", "evidence": ev,
            "reason": f"Output type {out_type!r} not mapped to an Article 50 paragraph.",
            "need": "Owner clarifies the use; Legal decides.", "owner": row.get("owner")}


def policy_assessments(sid: str, fx: dict, controls: dict) -> list[dict]:
    row = fx["row"]
    out = []
    notice = row.get("current_notice", "")
    states = fx["open_states"]
    recs = fx["records"]
    rec_ev = [ev_id("EVIDENCE", r["record_id"]) for r in recs]
    base_ev = fx["evidence_ids"][:1] + rec_ev

    def ctrl(cid):
        return controls.get(cid)

    if fx["derived"]["direct_interaction"]["value"] == "yes" and ctrl("CTRL-NOTICE"):
        c = ctrl("CTRL-NOTICE")
        e = base_ev + c["evidence_ids"]
        if "conflicting" in states:
            out.append(("NOTICE", "conflicting", c, e, f"Register says notice={notice!r} but evidence conflicts: " + "; ".join(r["notes"] for r in recs if r["evidence_state"] == "conflicting") + ". The stylised graphic alone does not establish what visitors understand.",
                        "System owner resolves which account of the notice is current."))
        elif notice == "no":
            out.append(("NOTICE", "supported-impact", c, e, "No first-interaction AI notice; confirmed by evidence: " + "; ".join(r["notes"] for r in recs) + ".", None))
        elif notice == "yes" and row.get("evidence_status") == "complete" and not states:
            out.append(("NOTICE", "supported-no-impact", c, e, "Notice in place and evidence complete: " + "; ".join(r["notes"] for r in recs) + ".", None))
        else:
            out.append(("NOTICE", "unresolved", c, e, f"Notice state {notice!r} with evidence {row.get('evidence_status')!r}.", "Owner supplies current notice evidence."))
    if row.get("output_type", "").startswith("synthetic_") and row.get("exposed_group") == "public" and ctrl("CTRL-SYNTHETIC"):
        c = ctrl("CTRL-SYNTHETIC")
        e = base_ev + c["evidence_ids"]
        prov = [r for r in recs if r["record_type"] != "exception_request"]
        pst = {r["evidence_state"] for r in prov if r["status"] != "closed"}
        if "conflicting" in pst:
            out.append(("SYNTHETIC", "conflicting", c, e, "Visible label recorded but provenance evidence conflicts: " + "; ".join(r["notes"] for r in prov) + ". A visible label does not prove machine-readable provenance.",
                        "Communications verifies provenance on the published copy."))
        elif pst & {"partial", "missing", "stale"} or notice != "visible_label":
            out.append(("SYNTHETIC", "unresolved", c, e, f"Label state {notice!r}; provenance not verified: " + "; ".join(r["notes"] for r in prov) + ".",
                        "Communications completes the provenance test."))
        else:
            out.append(("SYNTHETIC", "supported-no-impact", c, e, "Visible label and provenance evidence complete.", None))
    if row.get("output_type") == "text" and ctrl("CTRL-STAFF-DRAFT"):
        c = ctrl("CTRL-STAFF-DRAFT")
        e = base_ev + c["evidence_ids"]
        if "missing" in states or notice == "unknown":
            out.append(("STAFF-DRAFT", "unresolved", c, e, "Owner has not recorded how generated material reaches recipients: " + "; ".join(r["notes"] for r in recs) + ". Missing evidence is not converted to compliance or non-compliance.",
                        "Owner records the recipient disclosure practice; Legal confirms."))
        elif notice == "not_applicable" and row.get("evidence_status") == "complete":
            out.append(("STAFF-DRAFT", "supported-no-impact", c, e, "Staff-only use, outputs not sent outside the staff workspace; evidence complete.", None))
        else:
            out.append(("STAFF-DRAFT", "unresolved", c, e, f"Notice {notice!r}, evidence {row.get('evidence_status')!r}.", "Owner confirms."))
    if (row.get("evidence_status") == "stale" or "stale" in states) and ctrl("CTRL-REGISTER"):
        c = ctrl("CTRL-REGISTER")
        out.append(("EVIDENCE-CURRENCY", "unresolved", c, base_ev + c["evidence_ids"],
                    f"Evidence is stale (last updated {row.get('evidence_updated_at')}): " + "; ".join(r["notes"] for r in recs if r["evidence_state"] == "stale") + ".",
                    "Owner refreshes role and release evidence for the current release."))
    for r in recs:
        if r["record_type"] == "exception_request" and ctrl("CTRL-EXCEPTION"):
            c = ctrl("CTRL-EXCEPTION")
            out.append(("EXCEPTION", "unresolved", c, [ev_id("EVIDENCE", r["record_id"])] + c["evidence_ids"],
                        f"Exception request {r['record_id']} is {r['status']}: {r['notes']}. The automation may not approve it.",
                        "Legal decides the exception; it needs a named owner, rationale, expiry date and Legal approval."))
    return out


ACTION_TOPICS = {
    "ART50": ["provider-role", "release", "disclosure"],
    "NOTICE": ["notice", "disclosure"],
    "SYNTHETIC": ["provenance", "label"],
    "STAFF-DRAFT": ["recipient", "disclosure"],
    "EVIDENCE-CURRENCY": ["evidence", "provider-role", "release"],
    "EXCEPTION": ["exception"],
}


def match_actions(topic: str, actions: list[dict], state: str) -> list[dict]:
    if state == "supported-no-impact":
        return []
    keys = ACTION_TOPICS.get(topic, [])
    hits = [a for a in actions if any(k in a["action"].lower() for k in keys)]
    if topic == "ART50":
        hits = [a for a in hits if a["approval_required"] == "legal" and "exception" not in a["action"].lower()]
    if topic == "NOTICE" or topic == "STAFF-DRAFT":
        hits = [a for a in hits if "provenance" not in a["action"].lower()]
    return hits


def stage_impacts(run: Run, ev_out: dict, auth: dict) -> list[dict]:
    impacts, unaffected, conflicts, unresolved = [], [], [], []
    for sid, fx in ev_out["facts"].items():
        row = fx["row"]
        st = statutory_assessment(sid, fx, auth["authority_ok"], auth["binding"])
        items = [("ART50", st["state"], st["rule_ref"], st["evidence"], st["reason"], st["need"], st["owner"], "statutory (EU AI Act, binding)")]
        for topic, state, c, e, reason, need in policy_assessments(sid, fx, ev_out["controls"]):
            items.append((topic, state, f"{c['rule_ref']} [{c['id']}]", e, reason, need,
                          row.get("owner") if topic != "EXCEPTION" else "Legal", "internal policy (internal control)"))
        for topic, state, rule_ref, evs, reason, need, owner, basis in items:
            acts = match_actions(topic, fx["actions"], state)
            rec = {"id": f"IMP-{sid}-{topic}", "summary": f"{sid} {row.get('system_name')} — {rule_ref}: {state}",
                   "evidence_ids": sorted(set(evs + [ev_id("CALENDAR", a["action_id"]) for a in acts])),
                   "state": state, "system_id": sid, "system_name": row.get("system_name"), "rule_ref": rule_ref,
                   "rule_basis": basis, "owner": owner, "rationale": reason, "resolution_need": need,
                   "action_ids": [a["action_id"] for a in acts]}
            impacts.append(rec)
            if state == "supported-no-impact":
                unaffected.append({"id": f"UNAFF-{sid}-{topic}", "summary": rec["summary"], "evidence_ids": rec["evidence_ids"],
                                   "owner": owner, "rationale": reason, "impact_id": rec["id"]})
            elif state == "conflicting":
                conflicts.append({"id": f"CONF-{sid}-{topic}", "summary": rec["summary"], "evidence_ids": rec["evidence_ids"],
                                  "owner": owner, "rationale": reason, "resolution_need": need, "impact_id": rec["id"]})
            elif state == "unresolved":
                unresolved.append({"id": f"UNR-{sid}-{topic}", "summary": rec["summary"], "evidence_ids": rec["evidence_ids"],
                                   "owner": owner, "rationale": reason, "resolution_need": need, "impact_id": rec["id"]})
    s4 = run.snapshots[3]
    consumed = [r for r in s4["produced_record_ids"] if r.startswith(("FACT-", "CTRL-", "REC-"))] + \
               [r["id"] for r in run.snapshots[2]["state"]["binding_rules"]]
    status = "complete" if auth["authority_ok"] and ev_out["facts"] else ("blocked" if not ev_out["facts"] else "partial")
    state = {"impacts": impacts, "unaffected_items": unaffected, "conflicts": conflicts,
             "unresolved_items": unresolved,
             "scope_note": "Statutory rows assess Quillhaven's own Article 50 duties as of the review date; internal-policy rows assess AI-POL controls. They are kept as separate rule bases."}
    produced = [r["id"] for r in impacts + unaffected + conflicts + unresolved]
    run.write_snapshot("impact-analysis", status, state, consumed or [s4["produced_record_ids"][0]], produced,
                       conflicts + unresolved, [d for d in DECISIONS if d["stage"] == "impact-analysis"])
    return impacts


# ---------------------------------------------------------------------------
# Stage 06 — actions and approvals
# ---------------------------------------------------------------------------


def valid_date(s: str) -> bool:
    try:
        dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def stage_actions(run: Run, impacts: list[dict], ev_out: dict) -> dict:
    cal = run.data.get("SRC-CALENDAR")
    cal_rows = {a["action_id"]: a for a in cal["rows"]} if cal else {}
    cal_ver = ",".join((run.sources["SRC-CALENDAR"]["version_metadata"] or {}).get("record_versions") or []) if cal else None
    proposed, approvals, escalations, reviews = [], [], [], []
    linked: dict[str, list[str]] = {}
    for imp in impacts:
        for aid in imp["action_ids"]:
            linked.setdefault(aid, []).append(imp["id"])
    for aid, a in cal_rows.items():
        date_ok = valid_date(a["due_date"])
        role = {"legal": "Legal", "operations": "Operations"}.get(a["approval_required"].lower())
        rec = {"id": f"PA-{aid}", "summary": a["action"], "evidence_ids": [ev_id("CALENDAR", aid)],
               "action_id": aid, "system_id": a["system_id"], "owner": a["owner"],
               "responsible_role": a["owner"], "proposed_due_date": a["due_date"] if date_ok else None,
               "date_basis": f"CALENDAR {cal_ver} due_date (proposed; not changed by this automation)" if date_ok else None,
               "calendar_status": a["status"], "approval_role": role,
               "approval_status": "pending" if role else "not-required",
               "impact_ids": linked.get(aid, []),
               "rationale": "Existing calendar proposal carried forward unchanged."}
        if not date_ok:
            rec["undated_reason"] = f"due_date {a['due_date']!r} is not a valid date; omitted from the calendar"
        if a["status"] == "blocked":
            rec["blocked_note"] = "Calendar marks this action blocked; it stays tentative and needs the blocking decision first."
        if not role:
            escalations.append({"id": f"ESC-ROLE-{aid}", "summary": f"{aid} approval_required={a['approval_required']!r} is not a disclosed value",
                                "evidence_ids": [ev_id("CALENDAR", aid)], "owner": "Operations"})
        proposed.append(rec)
    # New proposals for impacts with no calendar action (undated; never invented dates)
    for imp in impacts:
        if imp["state"] != "supported-no-impact" and not imp["action_ids"]:
            nid = "PA-NEW-" + imp["id"][len("IMP-"):]
            proposed.append({"id": nid, "summary": f"{imp['owner']} to address: {imp['resolution_need'] or 'confirm the supported impact'}",
                             "evidence_ids": imp["evidence_ids"][:3], "action_id": nid, "system_id": imp["system_id"],
                             "owner": imp["owner"], "responsible_role": imp["owner"], "proposed_due_date": None,
                             "undated_reason": "No owner-approved date exists in CALENDAR; the automation does not invent deadlines.",
                             "approval_role": "Legal" if imp["rule_basis"].startswith("statutory") else "Operations",
                             "approval_status": "pending", "impact_ids": [imp["id"]],
                             "rationale": "Impact needs an owner decision but no calendar action exists."})
            imp["action_ids"].append(nid)
    # Approvals and review requests
    n = 0
    for imp in impacts:
        reviewer = "Legal" if imp["rule_basis"].startswith("statutory") or "EXCEPTION" in imp["id"] else "Operations"
        if imp["state"] == "supported-no-impact" and reviewer == "Operations":
            approvals.append({"id": f"APR-{imp['id']}", "summary": f"No policy action proposed for {imp['id']}",
                              "evidence_ids": imp["evidence_ids"][:2], "status": "not-required", "owner": reviewer,
                              "impact_id": imp["id"]})
            imp["approval_status"] = "not-required"
            continue
        n += 1
        rid = f"RR-{n:03d}"
        approvals.append({"id": f"APR-{imp['id']}", "summary": f"{reviewer} review of {imp['id']} ({imp['state']})",
                          "evidence_ids": imp["evidence_ids"][:4], "status": "pending", "owner": reviewer,
                          "impact_id": imp["id"], "review_request_id": rid})
        imp["approval_status"] = "pending"
        q = {"supported-impact": "Do you accept this supported impact and the proposed action/date?",
             "supported-no-impact": "Do you accept the no-impact interpretation for Quillhaven's role?",
             "conflicting": "Which account is current, and does the proposed action resolve the conflict?",
             "unresolved": "What evidence or decision resolves this item, and who supplies it?"}[imp["state"]]
        reviews.append({"id": rid, "summary": f"{imp['system_id']} {imp['rule_ref']}", "evidence_ids": imp["evidence_ids"][:4],
                        "subject": {"system_id": imp["system_id"], "impact_id": imp["id"], "action_ids": imp["action_ids"]},
                        "run_id": run.run_id, "source_versions": source_versions(run),
                        "question": q, "required_reviewer": reviewer, "owner": reviewer,
                        "status": "prepared-not-sent",
                        "note": "Prepared in the draft package; not sent. No reply is simulated."})
    for imp in impacts:
        if "EXCEPTION" in imp["id"]:
            escalations.append({"id": f"ESC-{imp['id']}", "summary": "Draft exception request without Legal approval or expiry date",
                                "evidence_ids": imp["evidence_ids"], "owner": "Legal",
                                "rationale": "Policy CTRL-EXCEPTION: only Legal can approve; the automation drafts nothing further."})
    f5 = ev_out["facts"].get("AI-005")
    if f5 and f5["derived"]["biometric_or_emotion"]["value"] == "unknown":
        escalations.append({"id": "ESC-AI-005-SCOPE", "summary": "AI-005 biometric/emotion facts are open. If the flagging infers emotions of learners, questions outside Article 50 (e.g. Article 5 prohibitions) may arise; this review draws no conclusion on them.",
                            "evidence_ids": f5["evidence_ids"], "owner": "Legal",
                            "rationale": "Out of this review's Article 50 scope; flagged so Legal can decide whether a separate review is needed."})
    s5 = run.snapshots[4]
    consumed = [i["id"] for i in impacts]
    state = {"proposed_actions": proposed, "approval_requirements": approvals, "escalations": escalations,
             "review_requests": reviews, "received_feedback": [],
             "feedback_note": "No reviewer feedback has been received through the facilitator's verified channel; all approvals remain pending."}
    produced = [r["id"] for r in proposed + approvals + escalations + reviews]
    run.write_snapshot("actions-and-approvals", "complete" if s5["status"] == "complete" else s5["status"],
                       state, consumed, produced, escalations, [d for d in DECISIONS if d["stage"] == "actions-and-approvals"])
    return {"proposed": proposed, "approvals": approvals, "escalations": escalations, "reviews": reviews}


def source_versions(run: Run) -> dict:
    out = {}
    for sid, s in run.sources.items():
        v = s.get("version_metadata") or {}
        out[sid] = (v.get("record_versions") or v.get("policy_version") or v.get("consolidation_date")
                    or v.get("oj_reference") or v.get("based_on_consolidation") or s.get("content_hash"))
        if isinstance(out[sid], list):
            out[sid] = ",".join(out[sid])
    return out


# ---------------------------------------------------------------------------
# Final drafts
# ---------------------------------------------------------------------------


def write_register(run: Run, impacts: list[dict], acts: dict) -> Path:
    pa = {p["action_id"]: p for p in acts["proposed"]}
    path = run.out / FINAL_FILES["ART-REGISTER"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(REGISTER_COLUMNS)
        for imp in impacts:
            a = [pa[x] for x in imp["action_ids"] if x in pa]
            dates = sorted({x["proposed_due_date"] for x in a if x.get("proposed_due_date")})
            reason = imp["rationale"]
            if a and not dates:
                reason += " Proposed action is undated: no owner-approved date exists."
            w.writerow([
                imp["id"], imp["system_id"], imp["rule_ref"], imp["state"], ";".join(imp["evidence_ids"]),
                reason, imp["owner"] or "",
                " | ".join(f"{x['action_id']}: {x['summary']}" for x in a),
                dates[0] if dates else "", imp.get("approval_status", "pending"),
                imp["system_name"], imp["rule_basis"], ";".join(imp["action_ids"]),
                imp["resolution_need"] or "", run.run_id,
            ])
    return path


def ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_fold(line: str) -> list[str]:
    out, b = [], line.encode("utf-8")
    while len(b) > 75:
        cut = 75 if not out else 74
        while (b[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b[cut:]
    out.append(b.decode("utf-8"))
    return [out[0]] + [" " + x for x in out[1:]]


def write_calendar(run: Run, acts: dict, authority_ok: bool, impacts: list[dict]) -> tuple[Path, list[str]]:
    stamp = run.started.replace("-", "").replace(":", "")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Quillhaven Academy//regulatory-change-impact-brief 1.0//EN",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:Article 50 proposed actions (draft)"]
    imp_by_id = {i["id"]: i for i in impacts}
    included = []
    for p in acts["proposed"]:
        if not p.get("proposed_due_date"):
            continue
        linked = [imp_by_id[i] for i in p["impact_ids"] if i in imp_by_id]
        # Without binding authority, statutory-dependent proposals are withheld.
        if not authority_ok and any(i["rule_basis"].startswith("statutory") for i in linked) and \
                not any(i["rule_basis"].startswith("internal") for i in linked):
            continue
        d = dt.date.fromisoformat(p["proposed_due_date"])
        basis = "; ".join(f"{i['id']} ({i['rule_ref']}, {i['state']})" for i in linked) or "CALENDAR register action (no linked impact this run)"
        desc = (f"Action {p['action_id']} | System {p['system_id']} | Responsible role: {p['responsible_role']} | "
                f"Basis: {basis} | Date basis: {p.get('date_basis')} | Approval: {p['approval_status']} "
                f"({p.get('approval_role') or 'none'}) | Calendar status: {p.get('calendar_status')} | Run {run.run_id} | "
                "DRAFT proposal; not an approved deadline.")
        ev = ["BEGIN:VEVENT", f"UID:{p['action_id']}@{UID_DOMAIN}", f"DTSTAMP:{stamp}",
              f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
              f"DTEND;VALUE=DATE:{(d + dt.timedelta(days=1)).strftime('%Y%m%d')}",
              "SUMMARY:" + ics_escape("[Proposed] " + p["action_id"] + " " + p["system_id"] + ": " + p["summary"]),
              f"DESCRIPTION:{ics_escape(desc)}", "STATUS:TENTATIVE", "TRANSP:TRANSPARENT", "END:VEVENT"]
        lines += ev
        included.append(p["action_id"])
    lines.append("END:VCALENDAR")
    folded = [x for line in lines for x in ics_fold(line)]
    path = run.out / FINAL_FILES["ART-CALENDAR"]
    path.write_bytes(("\r\n".join(folded) + "\r\n").encode("utf-8"))
    return path, included


def write_brief(run: Run, impacts: list[dict], acts: dict, included: list[str], auth: dict) -> Path:
    s = {k: [i for i in impacts if i["state"] == k] for k in ("supported-impact", "supported-no-impact", "conflicting", "unresolved")}
    status = run_status(run, auth)
    srcs = run.sources
    L = []
    L.append("# Article 50 compliance brief — DRAFT for review")
    L.append("")
    L.append(f"- **Run ID:** {run.run_id}")
    L.append(f"- **As-of (review) date:** {run.review_date} (sources retrieved {min(x['retrieved_at'] for x in srcs.values())} to {max(x['retrieved_at'] for x in srcs.values())})")
    L.append("- **Recipients:** Legal (final interpretation of the EU AI Act; exceptions) and Operations (policy activation, approved dates, incident closure). Prepared by the Compliance and Operations Manager. No delivery is claimed.")
    L.append(f"- **Status:** review-ready draft; run status `{status}`. Nothing here is legal advice, an approval, an activated policy or a changed deadline.")
    L.append(f"- **Package:** `impact-register.csv`, `action-calendar.ics`, snapshots in `snapshots/`. File hashes and review-request bindings are recorded in `snapshots/07-publication-validation.json`.")
    L.append("")
    L.append("## Source quality and limitations")
    L.append("")
    L.append("| Source | Role | Status | Version | Retrieved |")
    L.append("|---|---|---|---|---|")
    sv = source_versions(run)
    for sid, x in srcs.items():
        L.append(f"| {sid} | {x['source_role']} | {x['retrieval_status']} | {sv.get(sid) if x['retrieval_status'] == 'retrieved' else (x.get('reason') or '')} | {x['retrieved_at']} |")
    L.append("")
    L.append("- Binding basis: Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744, which was in force before the review date. The 27 July 2026 consolidation and the Service Desk page are navigation aids that were cross-checked, not relied on as the act.")
    L.append("- Company facts come from the Operations operating-facts context in the policy page, which records owner-supplied facts. Per that page, it does not prove provenance, refresh stale evidence or settle statutory applicability.")
    if not auth["authority_ok"]:
        L.append("- **Binding legal authority was unavailable or unsuitable this run.** Formal Article 50 conclusions are withheld (statutory rows unresolved). Policy-basis work continues, as the manager asked for useful unaffected work.")
    if run.failures:
        for f in run.failures:
            L.append(f"- Technical failure: {f['source_id']} at {f['stage']}: {f['reason']}. Recovery: {f['recovery']}")
    L.append("")
    L.append("## Supported observations")
    L.append("")
    L.append("Each conclusion is scoped either to **Quillhaven's own statutory duties under Article 50** or to **internal policy AI-POL controls**. The two are different rule bases.")
    L.append("")
    for k, title in (("supported-impact", "Supported impacts"), ("supported-no-impact", "Supported no-impact")):
        L.append(f"### {title}")
        L.append("")
        for i in s[k]:
            L.append(f"- **{i['id']}** ({i['rule_basis']}; {i['rule_ref']}): {i['rationale']} Evidence: {', '.join(i['evidence_ids'][:4])}.")
        if not s[k]:
            L.append("- None.")
        L.append("")
    L.append("## Conflicts and unresolved scope")
    L.append("")
    for i in s["conflicting"] + s["unresolved"]:
        L.append(f"- **{i['id']}** — {i['state']} ({i['rule_ref']}). {i['rationale']} **Needed:** {i['resolution_need']} **Owner:** {i['owner']}. Evidence: {', '.join(i['evidence_ids'][:4])}.")
    L.append("")
    if acts["escalations"]:
        L.append("### Escalations")
        L.append("")
        for e in acts["escalations"]:
            L.append(f"- **{e['id']}** ({e['owner']}): {e['summary']}")
        L.append("")
    L.append("## Proposed actions and dates")
    L.append("")
    L.append("Dates come only from the CALENDAR register and are carried forward unchanged as tentative proposals. Undated proposals are not in the calendar file.")
    L.append("")
    L.append("| Action | System | Responsible | Proposed date | In .ics | Approval | Linked impacts |")
    L.append("|---|---|---|---|---|---|---|")
    for p in acts["proposed"]:
        L.append(f"| {p['action_id']}: {p['summary']} | {p['system_id']} | {p['responsible_role']} | {p.get('proposed_due_date') or 'undated'} | {'yes' if p['action_id'] in included else 'no — ' + (p.get('undated_reason') or 'withheld')} | {p['approval_status']} ({p.get('approval_role') or '-'}) | {', '.join(p['impact_ids']) or '-'} |")
    L.append("")
    L.append("## Decisions requested from Legal and Operations")
    L.append("")
    L.append("Review requests are prepared here and have **not been sent**. The binding of each request to the exact hash of this brief is recorded in `snapshots/07-publication-validation.json`.")
    L.append("")
    L.append("| Request | Reviewer | Subject | Question | Evidence |")
    L.append("|---|---|---|---|---|")
    for r in acts["reviews"]:
        L.append(f"| {r['id']} | {r['required_reviewer']} | {r['subject']['impact_id']} (actions: {', '.join(r['subject']['action_ids']) or '-'}) | {r['question']} | {', '.join(r['evidence_ids'][:3])} |")
    L.append("")
    L.append(f"Source versions for every request: {'; '.join(f'{k}={v}' for k, v in source_versions(run).items())}.")
    L.append("")
    path = run.out / FINAL_FILES["ART-BRIEF"]
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def run_status(run: Run, auth: dict) -> str:
    req_fail = [s for s, x in run.sources.items() if x.get("required") and x["retrieval_status"] != "retrieved"]
    any_fail = [s for s, x in run.sources.items() if x["retrieval_status"] != "retrieved"]
    if not auth["authority_ok"]:
        return "blocked"
    if req_fail:
        return "partial"
    return "partial" if any_fail else "complete"


# ---------------------------------------------------------------------------
# Stage 07 — publication validation (and the standalone --verify)
# ---------------------------------------------------------------------------


def check_files(out: Path, impacts_ids: list[str] | None = None) -> list[dict]:
    checks = []

    def add(cid, ok, summary, evid=None):
        checks.append({"id": cid, "summary": summary, "evidence_ids": evid or [], "result": "pass" if ok else "fail"})

    reg = out / FINAL_FILES["ART-REGISTER"]
    brief = out / FINAL_FILES["ART-BRIEF"]
    ics = out / FINAL_FILES["ART-CALENDAR"]
    rows = []
    if reg.exists():
        with reg.open(encoding="utf-8", newline="") as fh:
            r = csv.DictReader(fh)
            hdr = r.fieldnames or []
            rows = list(r)
        add("CHK-REG-HEADER", hdr[:10] == REGISTER_COLUMNS[:10], "Register has the required columns in order")
        add("CHK-REG-STATES", all(x["state"] in ("supported-impact", "supported-no-impact", "conflicting", "unresolved") for x in rows), "Register states use the schema vocabulary")
        add("CHK-REG-APPROVAL", all(x["approval_status"] in ("pending", "approved", "rejected", "not-required") for x in rows), "Register approval statuses use the schema vocabulary")
        add("CHK-REG-DATES", all((not x["proposed_due_date"]) or valid_date(x["proposed_due_date"]) for x in rows), "Register dates are YYYY-MM-DD or blank")
        add("CHK-REG-UNIQUE", len({x["impact_id"] for x in rows}) == len(rows), "Impact IDs are unique")
        if impacts_ids is not None:
            add("CHK-REG-MATCH-S05", sorted(x["impact_id"] for x in rows) == sorted(impacts_ids), "Register rows match stage 05 impacts")
    else:
        add("CHK-REG-EXISTS", False, "impact-register.csv missing")
    btext = brief.read_text(encoding="utf-8") if brief.exists() else ""
    add("CHK-BRIEF-EXISTS", bool(btext), "compliance-brief.md present")
    if rows and btext:
        missing = [x["impact_id"] for x in rows if x["impact_id"] not in btext]
        add("CHK-BRIEF-CITES-IMPACTS", not missing, f"Brief cites every register impact ID (missing: {missing})")
        run_ids = {x["run_id"] for x in rows}
        add("CHK-RUN-ID-AGREES", len(run_ids) == 1 and next(iter(run_ids)) in btext, "Register and brief carry the same run ID")
    if ics.exists():
        raw = ics.read_bytes().decode("utf-8")
        unfolded = re.sub(r"\r\n[ \t]", "", raw)
        lines = unfolded.split("\r\n")
        add("CHK-ICS-CRLF", "\n" not in raw.replace("\r\n", ""), "Calendar uses CRLF line endings")
        add("CHK-ICS-HEADER", lines[0] == "BEGIN:VCALENDAR" and "VERSION:2.0" in lines and any(l.startswith("PRODID:") for l in lines)
            and lines[-2] == "END:VCALENDAR", "VCALENDAR with VERSION and PRODID")
        events = re.findall(r"BEGIN:VEVENT\r\n(.*?)\r\nEND:VEVENT", unfolded, re.S)
        ok = True
        uids = []
        for e in events:
            props = {l.split(":", 1)[0].split(";", 1)[0] for l in e.split("\r\n")}
            ok &= {"UID", "DTSTAMP", "DTSTART", "SUMMARY", "DESCRIPTION", "STATUS"} <= props
            ok &= "STATUS:TENTATIVE" in e and "DTSTART;VALUE=DATE:" in e
            uids.append(re.search(r"UID:(\S+)", e).group(1))
        add("CHK-ICS-EVENTS", ok, f"{len(events)} events carry UID, DTSTAMP, all-day DTSTART, SUMMARY, DESCRIPTION, STATUS:TENTATIVE")
        add("CHK-ICS-UID-UNIQUE", len(set(uids)) == len(uids), "Calendar UIDs are unique and action-linked")
        if rows:
            reg_actions = {a for x in rows for a in x.get("action_ids", "").split(";") if a}
            orphan = [u.split("@")[0] for u in uids if u.split("@")[0] not in reg_actions and u.split("@")[0] not in btext]
            add("CHK-ICS-AGREES", not orphan, f"Every calendar action appears in the register or brief (orphans: {orphan})")
    else:
        add("CHK-ICS-EXISTS", False, "action-calendar.ics missing")
    return checks


def stage_publication(run: Run, impacts: list[dict], acts: dict, auth: dict, schema: dict) -> str:
    import jsonschema
    checks = check_files(run.out, [i["id"] for i in impacts])
    # snapshot chain 01-06
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for i, p in enumerate(run.snapshot_paths):
        errs = list(validator.iter_errors(json.loads(p.read_text(encoding="utf-8"))))
        checks.append({"id": f"CHK-SCHEMA-S{i + 1:02d}", "summary": f"{p.name} conforms to snapshot.schema.json" + (f": {errs[0].message[:200]}" if errs else ""),
                       "evidence_ids": [run.snapshots[i]["snapshot_id"]], "result": "fail" if errs else "pass"})
    produced_all: set[str] = set()
    for i, sn in enumerate(run.snapshots):
        unresolved_ids = [c for c in sn["consumed_record_ids"] if c not in produced_all]
        if i > 0:
            checks.append({"id": f"CHK-CONSUMED-S{i + 1:02d}", "summary": f"{sn['stage']} consumed IDs resolve upstream" + (f" (unresolved: {unresolved_ids[:5]})" if unresolved_ids else ""),
                           "evidence_ids": [sn["snapshot_id"]], "result": "fail" if unresolved_ids else "pass"})
        produced_all |= set(sn["produced_record_ids"])
    known_ev = set(run.evidence) | {s["id"] for s in run.snapshots[1]["state"]["sources"]}
    bad_ev = sorted({e for i in impacts for e in i["evidence_ids"] if e not in known_ev})
    checks.append({"id": "CHK-EVIDENCE-RESOLVES", "summary": "Every impact evidence ID resolves to a captured extract or source attempt" + (f" (missing: {bad_ev[:5]})" if bad_ev else ""),
                   "evidence_ids": [], "result": "fail" if bad_ev else "pass"})
    for sid, s in run.sources.items():
        if s.get("local_reference"):
            ok = sha256_file(REPO_DIR / s["local_reference"]) == s["content_hash"]
            checks.append({"id": f"CHK-CAPTURE-{sid}", "summary": f"Captured bytes for {sid} match the recorded hash", "evidence_ids": [s["id"]],
                           "result": "pass" if ok else "fail"})
    artifacts = []
    for aid, fname in FINAL_FILES.items():
        p = run.out / fname
        artifacts.append({"id": aid, "path": rel(p), "sha256": sha256_file(p) if p.exists() else "sha256:" + "0" * 64,
                          "validation_status": "valid" if p.exists() else "not-produced"})
    any_fail = [c for c in checks if c["result"] == "fail"]
    for a in artifacts:
        if any_fail and a["validation_status"] == "valid":
            a["validation_status"] = "invalid"
    brief_art = next(a for a in artifacts if a["id"] == "ART-BRIEF")
    bindings = [{"review_request_id": r["id"], "required_reviewer": r["required_reviewer"], "impact_id": r["subject"]["impact_id"],
                 "reviewed_artifact_path": brief_art["path"], "reviewed_artifact_sha256": brief_art["sha256"],
                 "run_id": run.run_id, "status": r["status"]} for r in acts["reviews"]]
    if any_fail:
        pub = "failed"
    elif not auth["authority_ok"]:
        pub = "blocked"
    else:
        pub = "validated"
    status = {"validated": run_status(run, auth), "blocked": "blocked", "failed": "failed"}[pub]
    state = {"artifacts": artifacts, "validation_checks": checks, "publication_status": pub,
             "publication_note": "'validated' means the draft package passed internal validation. It is not a human approval or an external publication.",
             "review_request_bindings": bindings, "run_status": status,
             "technical_failures": run.failures}
    consumed = [r["id"] for r in acts["reviews"]] + [i["id"] for i in impacts]
    produced = [a["id"] for a in artifacts] + [c["id"] for c in checks]
    run.write_snapshot("publication-validation", status, state, consumed, produced,
                       [{"id": c["id"], "summary": c["summary"], "evidence_ids": c["evidence_ids"]} for c in any_fail],
                       [d for d in DECISIONS if d["stage"] == "publication-validation"])
    return pub


def verify_existing(out: Path, schema: dict) -> int:
    """Inspect the current package without fetching: snapshots, chain, captures, final files."""
    import jsonschema
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    problems = []
    snaps = []
    for i, stage in enumerate(STAGES, start=1):
        p = out / "snapshots" / f"{i:02d}-{stage}.json"
        if not p.exists():
            problems.append(f"missing snapshot {p.name}")
            continue
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"{p.name} is not valid JSON: {e}")
            continue
        for e in validator.iter_errors(s):
            problems.append(f"{p.name}: {e.message[:200]}")
        snaps.append((p, s))
    if len(snaps) == 7:
        run_ids = {s["run_id"] for _, s in snaps}
        if len(run_ids) != 1:
            problems.append(f"snapshots carry different run IDs: {run_ids}")
        for (pp, ps), (p, s) in zip(snaps, snaps[1:]):
            pred = s["predecessor"] or {}
            if pred.get("snapshot_id") != ps["snapshot_id"] or pred.get("sha256") != sha256_file(pp):
                problems.append(f"{p.name}: predecessor binding does not match {pp.name}")
        for src in snaps[1][1]["state"]["sources"]:
            if src.get("local_reference"):
                lp = REPO_DIR / src["local_reference"]
                if not lp.exists() or sha256_file(lp) != src["content_hash"]:
                    problems.append(f"captured source {src['local_reference']} missing or altered")
        final = snaps[6][1]["state"]
        for a in final["artifacts"]:
            ap = REPO_DIR / a["path"]
            if not ap.exists() or sha256_file(ap) != a["sha256"]:
                problems.append(f"{a['path']} missing or changed since stage 07")
        impacts = [i["id"] for i in snaps[4][1]["state"]["impacts"]]
        for c in check_files(out, impacts):
            if c["result"] == "fail":
                problems.append(f"{c['id']}: {c['summary']}")
        if final["publication_status"] == "failed":
            problems.append("stage 07 recorded publication_status failed")
    if problems:
        print("VERIFY FAILED:")
        for p in problems:
            print(" -", p)
        print("Recovery: re-run the documented command (fresh source reads); the failed package is archived to history/.")
        return 1
    pub = snaps[6][1]["state"]["publication_status"]
    print(f"VERIFY OK: run {snaps[0][1]['run_id']}, 7 snapshots chained, captures and final files match stage 07; "
          f"publication_status {pub}, run status {snaps[6][1]['status']}.")
    if pub == "blocked":
        print("The package is internally consistent but BLOCKED: required legal authority was unavailable. Re-run when the routes respond.")
        return 3
    return 0


# ---------------------------------------------------------------------------
# Project decisions (recorded in the snapshots of the stage they govern)
# ---------------------------------------------------------------------------

def _dec(i, stage, summary, concern, options, basis, chosen, rationale, tradeoffs, effect, evidence):
    return {"id": i, "stage": stage, "summary": summary, "concern": concern, "options": options,
            "source_basis": basis, "chosen_behavior": chosen, "rationale": rationale, "tradeoffs": tradeoffs,
            "downstream_effect": effect, "evidence_ids": evidence, "owner": "Automation specialist (Ricardo)"}


DECISIONS = [
    _dec("DEC-01", "scope", "Review date is fixed; retrieval time is separate",
         "Sources are read in October but the review is as of 26 August 2026.",
         ["Use retrieval date as as-of date", "Use assigned review date and record retrieval times separately"],
         "Assignment scenario; interview 03:34 PM ('The review is as of August 26, 2026').",
         "as_of is always the --review-date; every source attempt records its actual retrieved_at.",
         "Conclusions must be about the legal and factual position on the review date.",
         ["Later legal changes are not reflected unless the review date is changed by a human"],
         "Stage 03 checks each legal version was effective by the review date.", []),
    _dec("DEC-02", "source-capture", "Read every disclosed route live; never substitute a local copy",
         "A failed read could tempt a fallback to stored files.",
         ["Fall back to the last good capture", "Record the failure and continue with what is supportable"],
         "Starter README; interview 03:33 PM ('produce useful unaffected work while maintaining clear visibility on the limits').",
         "Each run fetches all 10 routes with retries; failures are kept as attempts with null hash.",
         "A stale copy would hide the gap the reviewers need to see.",
         ["A network outage yields a partial or blocked package instead of a complete one"],
         "Stage 03-05 mark dependent items unresolved; the brief lists the failure.", []),
    _dec("DEC-03", "authority-and-timing", "Binding basis is the OJ act plus the OJ amendment; consolidation is navigation only",
         "Several legal routes say slightly different things about which text counts.",
         ["Rely on the Service Desk/consolidated text", "Rely on OJ texts and cross-check navigation aids"],
         "Interview 03:34 PM: 'The July 27, 2026, consolidation is a navigation aid, not a separate legal act. We always check LAW, OJ, AMEND, and CONSOLIDATED.'",
         "Art. 50 paragraphs are extracted from the OJ text; Art. 50(7) and Art. 111(4) from Regulation (EU) 2026/1744; consolidated and Service Desk texts are compared, not cited as binding.",
         "Only the OJ publications are legally authentic.",
         ["More parsing of large EUR-Lex pages", "If the OJ page changes layout the run blocks rather than falling back"],
         "Statutory register rows cite RULE-ART50-* evidence from the OJ source.", []),
    _dec("DEC-04", "evidence-reconciliation", "Field meanings are disclosed, not guessed",
         "Register values could be renamed or extended.",
         ["Map unknown columns heuristically", "Require the disclosed fields and report anything else"],
         "Interview 03:35 PM (status values) and policy CTRL-EVIDENCE-STATES.",
         "Columns are found by header name (any order, extra columns allowed); missing fields or undisclosed values are reported as gaps.",
         "Guessing a renamed field could silently change a business meaning.",
         ["A legitimate rename needs a config change before the run is complete"],
         "Unknown values become unresolved items with an owner.", []),
    _dec("DEC-05", "impact-analysis", "Separate statutory and internal-policy rule bases",
         "Internal policy is stricter than Article 50 for deployers (e.g. notices for direct interaction).",
         ["Merge into one compliance verdict", "Keep one row per system per rule basis"],
         "Interview 03:24 PM ('use the binding Article 50 text and the internal policy to evaluate our controls'); policy approval boundary.",
         "Each register row has rule_ref and rule_basis; statutory rows go to Legal, policy rows to Operations.",
         "Legal and Operations own different decisions; mixing bases would misstate legal exposure.",
         ["More rows for reviewers to read"],
         "Approval requirements are routed by rule basis.", []),
    _dec("DEC-06", "impact-analysis", "Quillhaven's role is taken from the register and corroborated by the policy operating facts",
         "Provider duties (50(1), 50(2)) and deployer duties (50(3), 50(4)) differ.",
         ["Assume deployer for all", "Use register role, corroborate with the policy context, unresolved when either is open"],
         "SYSTEMS provider_role/deployer_role; policy 'Operating scope' paragraph.",
         "Deployer-only when both agree; unknown (AI-005) stays unresolved with the owner's refresh as the need.",
         "Role decides which paragraph applies; it must not be assumed.",
         ["Conclusions for supplier products depend on owner-supplied facts that the policy says are not Legal decisions"],
         "Statutory no-impact rows explain that provider duties sit with the supplier and ask Legal to confirm.", []),
    _dec("DEC-07", "actions-and-approvals", "Dates only from CALENDAR; undated proposals stay out of the .ics",
         "The automation could propose its own deadlines.",
         ["Invent target dates", "Carry calendar dates forward unchanged and leave new proposals undated"],
         "Interview 03:32 PM (owners and dates live in the calendar sheet); policy approval boundary (may not change a production deadline).",
         "Calendar actions become TENTATIVE events; new needs are undated proposals explained in register and brief.",
         "Operations owns operational deadlines.",
         ["Some needs (e.g. AI-008 Art. 50(4) confirmation) have no date until an owner sets one"],
         "action-calendar.ics contains only calendar-backed dates.", []),
    _dec("DEC-08", "publication-validation", "Validated means internally consistent, not approved",
         "A green validation could be read as sign-off.",
         ["Report 'published'", "Report 'validated' with an explicit note and pending approvals"],
         "Assignment publication rules; interview 03:33 PM (no delivery claimed without evidence).",
         "Stage 07 checks schema, chain, hashes and cross-file agreement; review requests are bound to the brief hash and marked prepared-not-sent.",
         "Reviewers must be able to tell exactly which draft they are asked to approve.",
         ["Every rerun changes the brief hash, so earlier requests no longer match"],
         "Unmatched future feedback stays unresolved.", []),
]
for _d in DECISIONS:
    _d["evidence_ids"] = ["EV-INTERVIEW"]


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--review-date", default="2026-08-26", help="assigned review date (YYYY-MM-DD)")
    ap.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="source routes JSON (interview-disclosed)")
    ap.add_argument("--scope", type=Path, default=DEFAULT_SCOPE, help="review scope JSON")
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reason", default="scheduled run", help="why this run or retry happens (stage 01)")
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--retry-wait", type=int, default=20, help="seconds before retry n (multiplied by n)")
    ap.add_argument("--verify", action="store_true", help="inspect the existing package only; no fetching")
    args = ap.parse_args(argv)
    args.out = args.out.resolve()
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    if args.verify:
        return verify_existing(args.out, schema)
    try:
        dt.date.fromisoformat(args.review_date)
    except ValueError:
        print(f"invalid --review-date {args.review_date!r}", file=sys.stderr)
        return 2
    sources_cfg = json.loads(args.sources.read_text(encoding="utf-8"))["sources"]
    scope_cfg = json.loads(args.scope.read_text(encoding="utf-8"))

    args.out.mkdir(parents=True, exist_ok=True)
    hist = archive_previous(args.out)
    run = Run(args)
    print(f"run {run.run_id} (review date {run.review_date}); previous run: {hist['supersedes_run_id']}")
    stage_scope(run, scope_cfg, hist)
    stage_capture(run, sources_cfg)
    for sid, s in run.sources.items():
        print(f"  {sid:15s} {s['retrieval_status']:10s} {s.get('reason') or ''}")
    auth = stage_authority(run)
    ev_out = stage_evidence(run, scope_cfg)
    impacts = stage_impacts(run, ev_out, auth)
    acts = stage_actions(run, impacts, ev_out)
    write_register(run, impacts, acts)
    _, included = write_calendar(run, acts, auth["authority_ok"], impacts)
    write_brief(run, impacts, acts, included, auth)
    write_extracts(run)
    pub = stage_publication(run, impacts, acts, auth, schema)
    counts = {k: sum(1 for i in impacts if i["state"] == k) for k in ("supported-impact", "supported-no-impact", "conflicting", "unresolved")}
    print(f"impacts: {counts}; calendar events: {len(included)}; publication_status: {pub}")
    rc = verify_existing(args.out, schema)
    return 0 if pub == "validated" and rc == 0 else (3 if pub == "blocked" else 1)


if __name__ == "__main__":
    sys.exit(main())
