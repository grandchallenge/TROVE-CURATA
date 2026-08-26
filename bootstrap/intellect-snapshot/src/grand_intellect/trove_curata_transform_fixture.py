"""CLI entry point for TC-FIXTURE-003."""

from __future__ import annotations

import argparse
from pathlib import Path

from .trove_curata_transform_contract import canonical_json_bytes, load_manifest, provider_versions
from .trove_curata_transform_engine import transform_fragment_with_presidio
from .trove_curata_transform_report import build_report


def run_fixture(manifest_path: str | Path, output_path: str | Path, *, use_provider: bool = True) -> dict:
    manifest_path = Path(manifest_path)
    manifest = load_manifest(manifest_path)
    versions = provider_versions() if use_provider else {
        "presidio-anonymizer": "2.2.363",
        "presidio-analyzer": "2.2.363",
        "regex": "2026.7.19",
    }
    provider = None
    if use_provider:
        provider = lambda text, entity, operator, parameters: transform_fragment_with_presidio(
            text, entity, operator, parameters, versions
        )
    report = build_report(manifest, manifest_path.parent, versions, provider_transform=provider)
    Path(output_path).write_bytes(canonical_json_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute TC-FIXTURE-003")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run_fixture(args.manifest, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
