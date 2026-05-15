#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from maintenance_jobs import rebuild_mapping_from_scratch, refresh_documents_from_mapping  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild a project's shared mapping from scratch and optionally refresh "
            "existing documents with minimal reference-only updates."
        )
    )
    parser.add_argument("project_id", help="Project id under projects/<id>/project.json")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of items to include in each map rebuild batch (default: 20).",
    )
    parser.add_argument(
        "--refresh-documents",
        action="store_true",
        help="After rebuilding the map, minimally refresh existing documents to repair references.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only rebuild the first N excerpted non-text items in project order.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create project.json / mapping file backups before mutating files.",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> dict:
    rebuild_result = await rebuild_mapping_from_scratch(
        args.project_id,
        batch_size=args.batch_size,
        backup=not args.no_backup,
        limit=args.limit,
    )
    result = {"rebuildMapping": rebuild_result}
    if args.refresh_documents:
        result["refreshDocuments"] = await refresh_documents_from_mapping(
            args.project_id,
            backup=False,
        )
    return result


def main() -> int:
    args = parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
