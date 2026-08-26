#!/usr/bin/env python3
"""Cold-path agent-surface smoke check (portable, stdlib + okf doctor)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [
    "IDENTITY.md",
    "CONTEXT.md",
    "AGENTS.md",
    "_config/taxonomy.md",
    "_config/conventions.md",
    "_config/glossary.md",
    "rules/path-access-control.md",
    "skills/okf-core/SKILL.md",
    "skills/okf-ingest/SKILL.md",
    "skills/okf-journal/SKILL.md",
    "skills/okf-query/SKILL.md",
    "skills/okf-ingest/stages/01-snapshot/CONTEXT.md",
    "skills/okf-ingest/stages/04-relink-index/CONTEXT.md",
    "skills/okf-ingest-channel/stages/01-fetch/CONTEXT.md",
    "skills/okf-ingest-channel/stages/08-qa/CONTEXT.md",
    "skills/okf-icm-sync/SKILL.md",
    "tools/ingest_postprocess.py",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    for p in missing:
        print(f"missing: {p}")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8") if (ROOT / "AGENTS.md").exists() else ""
    n = agents.count("# OKF Brain — Operating Contract")
    if n != 1:
        print(f"AGENTS Operating Contract count={n}, want 1")
        missing.append("AGENTS.md#dup")
    # doctor
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "okf.py"), "doctor"], cwd=ROOT)
    # icm-sync report
    subprocess.run([sys.executable, str(ROOT / "tools" / "okf.py"), "icm-sync"], cwd=ROOT)
    if missing or r.returncode != 0:
        print("smoke: FAIL")
        return 1
    print("smoke: OK (required files present, AGENTS unique, doctor exited 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
