from __future__ import annotations
from typing import Any, Callable
from .trove_curata_duplicate_contract import content_id, require
from .trove_curata_duplicate_similarity import normalize_duplicate_text, normalize_predecessor_text, tokenize, shingle_set, score_text, jaccard_score
from .trove_curata_duplicate_minhash import pure_minhash_values, simulate_datasketch_score, score_with_datasketch
from .trove_curata_duplicate_chain import derive_tc003_baseline_output, build_record_contexts

def evaluate_pair(case: dict[str, Any], contexts: dict[str, dict[str, Any]], configuration: dict[str, Any], configuration_sha256: str, provider_scorer: Callable[[set[str], set[str]], float]) -> dict[str, Any]:
    left_id, right_id = sorted((case['left_record_id'], case['right_record_id']))
    require(left_id != right_id, 'self-pair detected')
    require(left_id in contexts and right_id in contexts, 'pair references missing record')
    left = contexts[left_id]
    right = contexts[right_id]
    exact_byte = left['raw_sha256'] == right['raw_sha256']
    normalized_equal = left['normalized_sha256'] == right['normalized_sha256']
    baseline_value = jaccard_score(left['shingles'], right['shingles'])
    provider_value = provider_scorer(left['shingles'], right['shingles'])
    threshold = float(configuration['threshold'])
    baseline_threshold = baseline_value >= threshold
    provider_threshold = provider_value >= threshold
    disagreement = baseline_threshold != provider_threshold
    conservative = left['record_class'] in configuration['conservative_record_classes'] or right['record_class'] in configuration['conservative_record_classes']
    if exact_byte:
        admitted_edge = True
        edge_basis = 'exact_byte'
    elif normalized_equal:
        admitted_edge = True
        edge_basis = 'normalized_text'
    elif baseline_threshold and provider_threshold and (not conservative):
        admitted_edge = True
        edge_basis = 'approximate_joint'
    else:
        admitted_edge = False
        edge_basis = 'none'
    route = 'duplicate_review_required' if admitted_edge or disagreement or (conservative and (baseline_threshold or provider_threshold)) else 'no_duplicate_observation'
    identity_payload = {'left_record_evidence_id': left['record_evidence_id'], 'right_record_evidence_id': right['record_evidence_id'], 'configuration_sha256': configuration_sha256}
    pair_id = content_id('curata-duplicate-pair', identity_payload)
    observation_payload = {'pair_id': pair_id, 'exact_byte_equal': exact_byte, 'normalized_text_equal': normalized_equal, 'provider_score': score_text(provider_value), 'baseline_score': score_text(baseline_value), 'threshold': configuration['threshold'], 'provider_threshold_met': provider_threshold, 'baseline_threshold_met': baseline_threshold, 'conservative_handling': conservative, 'disagreement_present': disagreement, 'admitted_edge': admitted_edge, 'edge_basis': edge_basis}
    observation_id = content_id('curata-duplicate-observation', observation_payload)
    routing_payload = {'observation_id': observation_id, 'route': route, 'routing_authority': 'grandchallenge'}
    return {'case_id': case['case_id'], 'case_class': case['case_class'], 'pair_id': pair_id, 'left_record_id': left_id, 'right_record_id': right_id, 'left_record_evidence_id': left['record_evidence_id'], 'right_record_evidence_id': right['record_evidence_id'], 'exact_byte_equal': exact_byte, 'normalized_text_equal': normalized_equal, 'provider_observation': {'provider': {'name': 'datasketch', 'version': configuration['provider']['version'], 'scheme': configuration['provider']['scheme'], 'num_perm': configuration['provider']['num_perm'], 'seed': configuration['provider']['seed']}, 'score': score_text(provider_value), 'threshold_met': provider_threshold, 'may_authorize_edge': False, 'may_authorize_route': False, 'may_delete_records': False}, 'baseline_observation': {'provider': configuration['baseline'], 'score': score_text(baseline_value), 'threshold_met': baseline_threshold}, 'conservative_handling': conservative, 'disagreement_present': disagreement, 'admitted_edge': admitted_edge, 'edge_basis': edge_basis, 'observation_id': observation_id, 'routing_record': {'routing_record_id': content_id('curata-duplicate-routing', routing_payload), **routing_payload, 'deletion_state': 'not_deleted', 'suppression_state': 'not_suppressed', 'canonical_member': None, 'admission_state': 'not_admitted'}}

def build_components(pair_observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parent: dict[str, str] = {}

    def find(value: str) -> str:
        parent.setdefault(value, value)
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        left_root, right_root = (find(left), find(right))
        if left_root != right_root:
            smaller, larger = sorted((left_root, right_root))
            parent[larger] = smaller
    for observation in pair_observations:
        find(observation['left_record_id'])
        find(observation['right_record_id'])
        if observation['admitted_edge']:
            union(observation['left_record_id'], observation['right_record_id'])
    members_by_root: dict[str, list[str]] = {}
    for record_id in sorted(parent):
        members_by_root.setdefault(find(record_id), []).append(record_id)
    components: list[dict[str, Any]] = []
    for members in sorted((sorted(values) for values in members_by_root.values() if len(values) > 1)):
        member_set = set(members)
        edges = sorted((observation['observation_id'] for observation in pair_observations if observation['admitted_edge'] and observation['left_record_id'] in member_set and (observation['right_record_id'] in member_set)))
        payload = {'members': members, 'admitted_observation_ids': edges}
        components.append({'component_id': content_id('curata-duplicate-component', payload), **payload, 'component_authority': 'grandchallenge', 'canonical_member': None, 'deletion_authorized': False, 'admission_authorized': False})
    return components
