from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .trove_curata_duplicate_contract import TroveCurataDuplicateError, content_id, require, sha256_bytes
from .trove_curata_duplicate_similarity import normalize_duplicate_text, normalize_predecessor_text, shingle_set

def _apply_operation(fragment: str, operation: dict[str, Any]) -> str:
    operator = operation['operator']
    parameters = operation['parameters']
    if operator == 'replace':
        return parameters['new_value']
    if operator == 'keep':
        return fragment
    if operator == 'mask':
        count = parameters['chars_to_mask']
        mask = parameters['masking_char'] * count
        return fragment[:-count] + mask if parameters['from_end'] else mask + fragment[count:]
    raise TroveCurataDuplicateError(f'unsupported predecessor operator: {operator}')

def derive_tc003_baseline_output(tc003_manifest_path: str | Path, case_id: str) -> str:
    tc003_path = Path(tc003_manifest_path)
    tc003 = json.loads(tc003_path.read_text(encoding='utf-8'))
    require(tc003.get('fixture_id') == 'TC-FIXTURE-003', 'wrong predecessor fixture')
    cases = {case['case_id']: case for case in tc003['cases']}
    require(case_id in cases, f'unknown TC003 case: {case_id}')
    case = cases[case_id]
    require(case['expected_plan_status'] == 'accepted', 'only accepted TC003 plans may supply retained outputs')
    tc002_path = tc003_path.parent / tc003['predecessor_manifest']
    tc002 = json.loads(tc002_path.read_text(encoding='utf-8'))
    tc002_cases = {item['case_id']: item for item in tc002['cases']}
    require(case['predecessor_case_id'] in tc002_cases, 'missing TC002 source case')
    source_case = tc002_cases[case['predecessor_case_id']]
    source_path = tc002_path.parent / source_case['path']
    source = normalize_predecessor_text(source_path.read_text(encoding='utf-8'))
    require(sha256_bytes(source.encode('utf-8')) == case['source_sha256'], 'TC003 source digest drift')
    operations = sorted(case['operations'], key=lambda item: (item['start_char'], item['end_char'], item['observation_id']))
    cursor = 0
    output: list[str] = []
    for operation in operations:
        start = operation['start_char']
        end = operation['end_char']
        require(0 <= cursor <= start < end <= len(source), 'TC003 operation span drift')
        output.append(source[cursor:start])
        output.append(_apply_operation(source[start:end], operation))
        cursor = end
    output.append(source[cursor:])
    return ''.join(output)

def build_record_contexts(records_payload: dict[str, Any], tc003_manifest_path: str | Path) -> dict[str, dict[str, Any]]:
    contexts: dict[str, dict[str, Any]] = {}
    for record in records_payload['records']:
        retained_text = record['text']
        origin = record['origin']
        if origin['kind'] == 'tc003_baseline_output':
            derived = derive_tc003_baseline_output(tc003_manifest_path, origin['case_id'])
            require(retained_text == derived, f"retained predecessor output drift: {record['record_id']}")
        raw_sha256 = sha256_bytes(retained_text.encode('utf-8'))
        normalized = normalize_duplicate_text(retained_text)
        payload = {'record_id': record['record_id'], 'record_class': record['record_class'], 'language': record['language'], 'origin': origin, 'raw_sha256': raw_sha256, 'normalized_sha256': sha256_bytes(normalized.encode('utf-8')), 'byte_length': len(retained_text.encode('utf-8'))}
        contexts[record['record_id']] = {**payload, 'record_evidence_id': content_id('curata-duplicate-record', payload), 'text': retained_text, 'normalized_text': normalized, 'shingles': shingle_set(retained_text)}
    return contexts
