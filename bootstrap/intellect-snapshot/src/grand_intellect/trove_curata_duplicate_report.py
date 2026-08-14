from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
from .trove_curata_duplicate_contract import FALSE_CLAIMS, FIXTURE_ID, PREDECESSOR, SCHEMA_VERSION, canonical_json_bytes, require, sha256_bytes
from .trove_curata_duplicate_engine import build_components, build_record_contexts, evaluate_pair

def _assemble_report(manifest: dict[str, Any], records_payload: dict[str, Any], fixture_root: str | Path, versions: dict[str, str], provider_scorer: Callable[[set[str], set[str]], float]) -> dict[str, Any]:
    root = Path(fixture_root)
    predecessor_path = root / manifest['predecessor_manifest']
    contexts = build_record_contexts(records_payload, predecessor_path)
    referenced = {record_id for case in manifest['cases'] for record_id in (case['left_record_id'], case['right_record_id'])}
    require(referenced == set(contexts), 'retained record coverage drift')
    configuration = {**manifest['configuration'], 'installed_provider_versions': versions, 'exact_digest_precedes_approximation': True, 'pair_order': 'lexicographic_record_id', 'edge_authority': 'gcl_owned_configuration', 'component_authority': 'gcl_owned_admitted_edges', 'provider_role': 'observation_only', 'source_records_immutable': True, 'external_project_dependency': False, 'network_required_for_replay': False}
    configuration_sha256 = sha256_bytes(canonical_json_bytes(configuration))
    record_reports = []
    for record_id in sorted(contexts):
        context = contexts[record_id]
        record_reports.append({'record_id': record_id, 'record_class': context['record_class'], 'language': context['language'], 'origin': context['origin'], 'raw_sha256': context['raw_sha256'], 'normalized_sha256': context['normalized_sha256'], 'byte_length': context['byte_length'], 'record_evidence_id': context['record_evidence_id'], 'source_record_mutated': False, 'deletion_state': 'not_deleted', 'suppression_state': 'not_suppressed', 'admission_state': 'not_admitted', 'canonical_member': None})
    case_manifest = {case['case_id']: case for case in manifest['cases']}
    pair_reports = []
    seen_pairs: set[tuple[str, str]] = set()
    for case_id in sorted(case_manifest):
        case = case_manifest[case_id]
        observation = evaluate_pair(case, contexts, manifest['configuration'], configuration_sha256, provider_scorer)
        pair = (observation['left_record_id'], observation['right_record_id'])
        require(pair[0] < pair[1], 'pair ordering drift')
        require(pair not in seen_pairs, 'duplicate pair observation')
        seen_pairs.add(pair)
        route = observation['routing_record']['route']
        checks = {'exact_byte_matches': observation['exact_byte_equal'] is case['expected_exact_byte'], 'normalized_text_matches': observation['normalized_text_equal'] is case['expected_normalized_text'], 'provider_threshold_matches': observation['provider_observation']['threshold_met'] is case['expected_provider_threshold'], 'baseline_threshold_matches': observation['baseline_observation']['threshold_met'] is case['expected_baseline_threshold'], 'admitted_edge_matches': observation['admitted_edge'] is case['expected_admitted_edge'], 'disagreement_matches': observation['disagreement_present'] is case['expected_disagreement'], 'edge_basis_matches': observation['edge_basis'] == case['expected_edge_basis'], 'route_matches': route == case['expected_route'], 'provider_has_no_authority': not observation['provider_observation']['may_authorize_edge'] and (not observation['provider_observation']['may_authorize_route']) and (not observation['provider_observation']['may_delete_records']), 'no_record_action': observation['routing_record']['deletion_state'] == 'not_deleted' and observation['routing_record']['suppression_state'] == 'not_suppressed' and (observation['routing_record']['admission_state'] == 'not_admitted') and (observation['routing_record']['canonical_member'] is None)}
        pair_reports.append({**observation, 'checks': checks, 'passed': all(checks.values())})
    components = build_components(pair_reports)
    component_members = [component['members'] for component in components]
    component_checks = {'expected_membership_matches': component_members == manifest['expected_components'], 'components_use_only_admitted_edges': all((all((any((pair['observation_id'] == observation_id and pair['admitted_edge'] for pair in pair_reports)) for observation_id in component['admitted_observation_ids'])) for component in components)), 'no_canonical_member_selected': all((component['canonical_member'] is None for component in components)), 'no_component_action': all((not component['deletion_authorized'] and (not component['admission_authorized']) for component in components))}
    report = {'schema_version': SCHEMA_VERSION, 'fixture_id': FIXTURE_ID, 'predecessor': PREDECESSOR, 'configuration': configuration, 'configuration_sha256': configuration_sha256, 'record_count': len(record_reports), 'records': record_reports, 'pair_count': len(pair_reports), 'pairs': pair_reports, 'components': components, 'component_checks': component_checks, 'claims': {claim: False for claim in sorted(FALSE_CLAIMS)}, 'passed': all((pair['passed'] for pair in pair_reports)) and all(component_checks.values())}
    return report

def build_report(manifest: dict[str, Any], records_payload: dict[str, Any], fixture_root: str | Path, versions: dict[str, str], provider_scorer: Callable[[set[str], set[str]], float]) -> dict[str, Any]:
    from .trove_curata_duplicate_validation import validate_report
    report = _assemble_report(manifest, records_payload, fixture_root, versions, provider_scorer)
    validate_report(report, manifest, records_payload, fixture_root, versions, provider_scorer)
    require(report['passed'], 'fixture acceptance checks failed')
    return report
from .trove_curata_duplicate_validation import validate_report
