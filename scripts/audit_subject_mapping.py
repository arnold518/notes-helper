#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from mapping_audit import audit_subject_mapping, format_audit_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a subject's shared mapping file against current project entries."
    )
    parser.add_argument("subject_id", help="Subject id, e.g. linear-algebra")
    parser.add_argument(
        "--projects-dir",
        default=str(ROOT / "projects"),
        help="Project storage directory (default: ./projects)",
    )
    parser.add_argument(
        "--include-sections",
        action="store_true",
        help="Include section labels in the missing-row details.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=12,
        help="Maximum labels to show per project/location in text output.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full audit report as JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_subject_mapping(Path(args.projects_dir), args.subject_id)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            format_audit_report(
                report,
                include_sections=args.include_sections,
                limit=max(1, int(args.limit)),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
