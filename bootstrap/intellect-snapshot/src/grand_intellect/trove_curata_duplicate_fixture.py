"""CLI for the TC-FIXTURE-004 duplicate-observation replay."""

from __future__ import annotations

import argparse
from pathlib import Path

from .trove_curata_duplicate_contract import (
    canonical_json_bytes,
    load_manifest,
    load_records,
    provider_versions,
)
from .trove_curata_duplicate_engine import score_with_datasketch
from .trove_curata_duplicate_report import build_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    records_payload = load_records(manifest_path.parent / manifest["records_file"])
    report = build_report(
        manifest,
        records_payload,
        manifest_path.parent,
        provider_versions(),
        score_with_datasketch,
    )
    Path(args.output).write_bytes(canonical_json_bytes(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
