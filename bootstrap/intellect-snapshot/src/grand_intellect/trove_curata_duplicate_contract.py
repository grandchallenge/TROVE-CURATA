from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .trove_curata_duplicate_identity import (
    EDGE_BASES,
    FALSE_CLAIMS,
    FIXTURE_ID,
    ORIGIN_KINDS,
    PERMUTATION_TABLE_SHA256,
    PREDECESSOR,
    PROVIDER_LOCK,
    RECORD_CLASSES,
    REQUIRED_CASE_CLASSES,
    ROUTES,
    SCHEMA_VERSION,
    TroveCurataDuplicateError,
    canonical_json_bytes,
    content_id,
    provider_versions,
    require,
    safe_relative_path,
    sha256_bytes,
)


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataDuplicateError(f"unable to load fixture manifest: {exc}") from exc

    require(isinstance(manifest, dict), "manifest root must be an object")
    require(
        set(manifest)
        == {
            "schema_version",
            "fixture_id",
            "predecessor",
            "authority",
            "records_file",
            "predecessor_manifest",
            "configuration",
            "cases",
            "expected_components",
        },
        "manifest field set drift",
    )
    require(manifest["schema_version"] == SCHEMA_VERSION, "manifest schema drift")
    require(manifest["fixture_id"] == FIXTURE_ID, "manifest identity drift")
    require(manifest["predecessor"] == PREDECESSOR, "predecessor identity drift")
    require(manifest["records_file"] == "records.json", "records file binding drift")
    require(
        manifest["predecessor_manifest"] == "../TC-FIXTURE-003/manifest.json",
        "predecessor manifest binding drift",
    )
    require(
        manifest["authority"]
        == {
            "project_owner": "grandchallenge",
            "repository": "grandchallenge/INTELLECT",
            "similarity_provider_role": "observation_only",
            "edge_authority": "gcl_owned_configuration",
            "component_authority": "gcl_owned_admitted_edges",
            "providers_may_authorize_routes": False,
            "providers_may_delete_records": False,
            "canonical_member_selection_enabled": False,
            "source_records_immutable": True,
            "external_project_dependency": False,
            "aether_required": False,
        },
        "authority boundary drift",
    )

    expected_configuration = {
        "normalization": "unicode_nfc_line_endings_whitespace_lower_v1",
        "tokenizer": "unicode_word_v1",
        "shingle_size": 3,
        "threshold": "0.720000",
        "provider": {
            "name": "datasketch",
            "version": "2.0.0",
            "numpy_version": "2.4.6",
            "scipy_version": "1.17.1",
            "scheme": "affine32",
            "num_perm": 128,
            "seed": 17,
            "permutation_table_sha256": PERMUTATION_TABLE_SHA256,
        },
        "baseline": {
            "name": "grand_intellect_jaccard",
            "version": SCHEMA_VERSION,
        },
        "conservative_record_classes": ["code_math", "short_text"],
    }
    require(manifest["configuration"] == expected_configuration, "configuration drift")

    cases = manifest["cases"]
    require(isinstance(cases, list) and cases, "fixture cases required")
    case_ids: set[str] = set()
    pair_ids: set[tuple[str, str]] = set()
    classes: set[str] = set()
    for case in cases:
        require(
            isinstance(case, dict)
            and set(case)
            == {
                "case_id",
                "case_class",
                "left_record_id",
                "right_record_id",
                "expected_exact_byte",
                "expected_normalized_text",
                "expected_provider_threshold",
                "expected_baseline_threshold",
                "expected_admitted_edge",
                "expected_disagreement",
                "expected_edge_basis",
                "expected_route",
            },
            "case field set drift",
        )
        case_id = case["case_id"]
        require(
            isinstance(case_id, str) and case_id and case_id not in case_ids,
            "invalid or duplicate case_id",
        )
        case_ids.add(case_id)
        require(case["case_class"] in REQUIRED_CASE_CLASSES, "unsupported case class")
        classes.add(case["case_class"])

        left = case["left_record_id"]
        right = case["right_record_id"]
        require(
            isinstance(left, str) and isinstance(right, str) and left and right,
            "record identities required",
        )
        require(left != right, "self-pairs are prohibited")
        pair = tuple(sorted((left, right)))
        require(pair not in pair_ids, "duplicate unordered pair identity")
        pair_ids.add(pair)

        for key in (
            "expected_exact_byte",
            "expected_normalized_text",
            "expected_provider_threshold",
            "expected_baseline_threshold",
            "expected_admitted_edge",
            "expected_disagreement",
        ):
            require(isinstance(case[key], bool), f"{key} must be boolean")
        require(case["expected_edge_basis"] in EDGE_BASES, "invalid edge basis")
        require(case["expected_route"] in ROUTES, "invalid route")

    require(classes == REQUIRED_CASE_CLASSES, "fixture class coverage drift")

    components = manifest["expected_components"]
    require(isinstance(components, list), "expected components must be a list")
    normalized_components: list[list[str]] = []
    seen_members: set[str] = set()
    for component in components:
        require(
            isinstance(component, list) and len(component) >= 2,
            "component requires at least two members",
        )
        require(
            component == sorted(component) and len(component) == len(set(component)),
            "component member order or uniqueness drift",
        )
        require(not seen_members & set(component), "expected components overlap")
        seen_members.update(component)
        normalized_components.append(component)
    require(normalized_components == sorted(normalized_components), "component order drift")
    return manifest


def load_records(path: str | Path) -> dict[str, Any]:
    records_path = Path(path)
    try:
        payload = json.loads(records_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataDuplicateError(f"unable to load retained records: {exc}") from exc

    require(isinstance(payload, dict), "records root must be an object")
    require(
        set(payload) == {"schema_version", "fixture_id", "records"},
        "records field set drift",
    )
    require(
        payload["schema_version"] == SCHEMA_VERSION and payload["fixture_id"] == FIXTURE_ID,
        "records identity drift",
    )
    require(isinstance(payload["records"], list) and payload["records"], "retained records required")

    ids: set[str] = set()
    for record in payload["records"]:
        require(
            isinstance(record, dict)
            and set(record) == {"record_id", "record_class", "language", "origin", "text"},
            "record field set drift",
        )
        record_id = record["record_id"]
        require(
            isinstance(record_id, str) and record_id and record_id not in ids,
            "invalid or duplicate record identity",
        )
        ids.add(record_id)
        require(record["record_class"] in RECORD_CLASSES, "invalid record class")
        require(record["language"] in {"en", "fr", "und"}, "invalid record language")

        origin = record["origin"]
        require(
            isinstance(origin, dict) and set(origin) == {"kind", "case_id"},
            "origin field drift",
        )
        require(origin["kind"] in ORIGIN_KINDS, "invalid origin kind")
        if origin["kind"] == "tc003_baseline_output":
            require(
                isinstance(origin["case_id"], str) and origin["case_id"],
                "TC003 origin case required",
            )
        else:
            require(
                origin["case_id"] is None,
                "fixture-retained origin must not name a predecessor case",
            )
        require(isinstance(record["text"], str) and record["text"], "retained text required")
    return payload


__all__ = [
    "EDGE_BASES",
    "FALSE_CLAIMS",
    "FIXTURE_ID",
    "ORIGIN_KINDS",
    "PERMUTATION_TABLE_SHA256",
    "PREDECESSOR",
    "PROVIDER_LOCK",
    "RECORD_CLASSES",
    "REQUIRED_CASE_CLASSES",
    "ROUTES",
    "SCHEMA_VERSION",
    "TroveCurataDuplicateError",
    "canonical_json_bytes",
    "content_id",
    "load_manifest",
    "load_records",
    "provider_versions",
    "require",
    "safe_relative_path",
    "sha256_bytes",
]
