from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
from .trove_curata_duplicate_contract import FALSE_CLAIMS, FIXTURE_ID, PREDECESSOR, ROUTES, SCHEMA_VERSION, canonical_json_bytes, require, sha256_bytes
from .trove_curata_duplicate_report import _assemble_report

def validate_report(report: dict[str, Any], manifest: dict[str, Any], records_payload: dict[str, Any], fixture_root: str | Path, versions: dict[str, str], provider_scorer: Callable[[set[str], set[str]], float]) -> None:
    require(set(report) == {'schema_version', 'fixture_id', 'predecessor', 'configuration', 'configuration_sha256', 'record_count', 'records', 'pair_count', 'pairs', 'components', 'component_checks', 'claims', 'passed'}, 'report field set drift')
    require(report['schema_version'] == SCHEMA_VERSION, 'report schema drift')
    require(report['fixture_id'] == FIXTURE_ID and report['predecessor'] == PREDECESSOR, 'report identity drift')
    require(report['configuration']['edge_authority'] == 'gcl_owned_configuration', 'edge authority drift')
    require(report['configuration']['component_authority'] == 'gcl_owned_admitted_edges', 'component authority drift')
    require(report['configuration']['provider_role'] == 'observation_only', 'provider role drift')
    require(report['configuration']['source_records_immutable'] is True, 'source immutability drift')
    require(report['configuration']['external_project_dependency'] is False, 'external project dependency introduced')
    require(report['configuration']['network_required_for_replay'] is False, 'network replay dependency introduced')
    require(report['configuration_sha256'] == sha256_bytes(canonical_json_bytes(report['configuration'])), 'configuration digest drift')
    require(set(report['claims']) == FALSE_CLAIMS, 'claim boundary field set drift')
    require(all((value is False for value in report['claims'].values())), 'claim inflation detected')
    require(isinstance(report['passed'], bool), 'report passed must be boolean')
    for pair in report['pairs']:
        require(pair['routing_record']['route'] in ROUTES, 'route escalation detected')
        require(pair['provider_observation']['may_authorize_edge'] is False, 'provider edge authority detected')
        require(pair['provider_observation']['may_authorize_route'] is False, 'provider route authority detected')
        require(pair['provider_observation']['may_delete_records'] is False, 'provider deletion authority detected')
        require(pair['routing_record']['canonical_member'] is None, 'canonical member selection detected')
        require(pair['routing_record']['deletion_state'] == 'not_deleted', 'deletion escalation detected')
        require(pair['routing_record']['suppression_state'] == 'not_suppressed', 'suppression escalation detected')
        require(pair['routing_record']['admission_state'] == 'not_admitted', 'admission escalation detected')
    expected = _assemble_report(manifest, records_payload, fixture_root, versions, provider_scorer)
    require(report == expected, 'canonical duplicate report drift')
