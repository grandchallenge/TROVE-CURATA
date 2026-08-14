"""Execute the governed TC-FIXTURE-002 provider replay."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .trove_curata_pii_analysis import analyze_with_presidio
from .trove_curata_pii_contract import canonical_json_bytes, load_manifest, normalize_text, provider_versions
from .trove_curata_pii_report import build_report


def run_fixture(manifest_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_manifest(manifest_file)
    root = manifest_file.parent
    versions = provider_versions()
    provider_rows: dict[str, list[dict[str, Any]]] = {}
    for case in manifest["cases"]:
        text = normalize_text((root / case["path"]).read_text(encoding="utf-8"))
        provider_rows[case["case_id"]] = analyze_with_presidio(
            text, case["language"], case["provider_rules"], versions
        )
    report = build_report(manifest, root, provider_rows, versions)
    Path(output_path).write_bytes(canonical_json_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args(argv)
    run_fixture(arguments.manifest, arguments.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
