from __future__ import annotations
import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any
FIXTURE_ID = 'TC-FIXTURE-004'
SCHEMA_VERSION = '0.1.0'
PREDECESSOR = {'fixture_id': 'TC-FIXTURE-003', 'subject_pull_request': 44, 'exact_merged_implementation_head': 'af5a568a2f49db949ff5c355f33ab29231cabac4', 'protected_implementation_merge': '0096eb21ca62c5ef7f6e458f358edcb1cd963a20', 'review_remedy_pull_request': 46, 'exact_remedy_head': '09ebdf7e1f01abc1dd75450725b4e8b0d93f3a65', 'protected_remedy_merge': '5c5f6a1cbb6327c559884a79abc119cf706153af'}
PROVIDER_LOCK = {'datasketch': '2.0.0', 'numpy': '2.4.6', 'scipy': '1.17.1'}
PERMUTATION_TABLE_SHA256 = '12bdcc189bfc2ff57ac116af1f714d22effe7a4253104dfa1be3c2d2f4239138'
ROUTES = {'no_duplicate_observation', 'duplicate_review_required'}
EDGE_BASES = {'exact_byte', 'normalized_text', 'approximate_joint', 'none'}
RECORD_CLASSES = {'general', 'boilerplate', 'short_text', 'code_math', 'multilingual'}
ORIGIN_KINDS = {'fixture_retained', 'tc003_baseline_output'}
REQUIRED_CASE_CLASSES = {'exact_byte_duplicate', 'normalized_text_duplicate', 'near_duplicate', 'reordered_sentences', 'shared_boilerplate_distinct', 'short_text_collision', 'code_math_conservative', 'multilingual_similarity', 'provider_baseline_disagreement', 'transitive_component', 'cross_origin_duplicate', 'negative_control', 'threshold_boundary_above', 'threshold_boundary_below'}
FALSE_CLAIMS = {'records_deleted', 'records_suppressed', 'canonical_member_selected', 'corpus_admitted', 'dataset_quality_proved', 'equivalence_proved', 'train_test_contamination_absent', 'privacy_compliance_proved', 'legality_proved', 'fitness_for_training_proved', 'production_release_authorized', 'downstream_improvement_proved', 'novelty_or_priority_claimed', 'commercial_claim_authorized'}

class TroveCurataDuplicateError(ValueError):
    """Raised when duplicate evidence, authority, or claims drift."""

def require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataDuplicateError(message)

def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def content_id(prefix: str, value: Any) -> str:
    return f'{prefix}:sha256:{sha256_bytes(canonical_json_bytes(value))}'

def safe_relative_path(value: Any) -> str:
    require(isinstance(value, str) and value, 'relative path required')
    require('://' not in value, 'network paths are prohibited')
    path = Path(value)
    require(not path.is_absolute(), 'absolute paths are prohibited')
    require('..' not in path.parts, 'path traversal prohibited')
    return value

def provider_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution, expected in PROVIDER_LOCK.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise TroveCurataDuplicateError(f'required provider not installed: {distribution}=={expected}') from exc
        require(actual == expected, f'provider identity drift: {distribution}=={actual}, expected {expected}')
        versions[distribution] = actual
    return versions
