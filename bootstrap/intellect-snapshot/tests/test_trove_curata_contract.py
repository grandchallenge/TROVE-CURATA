from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from grand_intellect.trove_curata_contract import (
    TroveCurataContractError,
    load_and_validate_trove_curata_contract,
    validate_trove_curata_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "governance" / "trove_curata_xref_work_package.json"
SCHEMA_PATH = ROOT / "schemas" / "trove_curata_xref_work_package.schema.json"


class TroveCurataContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def assert_rejected(self, mutate) -> None:
        candidate = copy.deepcopy(self.record)
        mutate(candidate)
        with self.assertRaises(TroveCurataContractError):
            validate_trove_curata_contract(candidate)

    def test_schema_is_closed_and_gcl_contained(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        authority = schema["properties"]["authority"]["properties"]
        self.assertEqual(authority["project_owner"]["const"], "grandchallenge")
        self.assertEqual(authority["project_scope"]["const"], "gcl_contained")
        self.assertFalse(authority["external_project_dependency"]["const"])
        self.assertEqual(
            authority["external_repositories_role"]["const"],
            "reference_only_non_authoritative",
        )
        self.assertEqual(authority["aether_role"]["const"], "future_projection_nonblocking")
        dependency = schema["properties"]["dependency_policy"]["properties"]
        self.assertFalse(dependency["external_project_repository_dependencies_allowed"]["const"])
        self.assertFalse(dependency["fixture_replay_requires_network"]["const"])

    def test_canonical_contract_is_valid(self) -> None:
        validated = load_and_validate_trove_curata_contract(CONTRACT_PATH)
        self.assertEqual(validated["work_package_id"], "TROVE-CURATA-XREF-WP00")
        self.assertEqual(validated["authority"]["project_scope"], "gcl_contained")

    def test_external_project_dependency_cannot_be_enabled(self) -> None:
        self.assert_rejected(
            lambda record: record["authority"].__setitem__("external_project_dependency", True)
        )

    def test_external_repository_cannot_gain_authority(self) -> None:
        self.assert_rejected(
            lambda record: record["authority"].__setitem__(
                "external_repositories_role", "implementation_authority"
            )
        )

    def test_external_repository_dependency_cannot_be_enabled(self) -> None:
        self.assert_rejected(
            lambda record: record["dependency_policy"].__setitem__(
                "external_project_repository_dependencies_allowed", True
            )
        )

    def test_pinned_open_source_providers_remain_allowed(self) -> None:
        self.assert_rejected(
            lambda record: record["dependency_policy"].__setitem__(
                "pinned_open_source_providers_allowed", False
            )
        )

    def test_provider_cannot_gain_policy_authority(self) -> None:
        self.assert_rejected(
            lambda record: record["dependency_policy"].__setitem__(
                "providers_have_policy_authority", True
            )
        )

    def test_future_repository_cannot_become_wp00_dependency(self) -> None:
        self.assert_rejected(
            lambda record: record["dependency_policy"].__setitem__(
                "future_dedicated_repository_required_for_wp00", True
            )
        )

    def test_aether_cannot_become_runtime_authority(self) -> None:
        self.assert_rejected(
            lambda record: record["authority"].__setitem__("aether_role", "required_runtime")
        )

    def test_record_contract_cannot_be_omitted(self) -> None:
        self.assert_rejected(lambda record: record["record_contracts"].pop())

    def test_review_tier_semantics_cannot_drift(self) -> None:
        self.assert_rejected(
            lambda record: record["review_tiers"].__setitem__(
                "T3", "ordinary_maintainer_review"
            )
        )

    def test_fixture_bytes_must_be_gcl_retained(self) -> None:
        self.assert_rejected(
            lambda record: record["fixture"].__setitem__(
                "fixture_bytes_authority", "external_repository"
            )
        )

    def test_fixture_replay_must_remain_offline(self) -> None:
        self.assert_rejected(
            lambda record: record["fixture"].__setitem__("network_required_for_replay", True)
        )

    def test_synthetic_content_cannot_be_enabled(self) -> None:
        self.assert_rejected(
            lambda record: record["fixture"].__setitem__("synthetic_content_allowed", True)
        )

    def test_claim_inflation_is_rejected(self) -> None:
        for claim in self.record["claim_boundary"]:
            with self.subTest(claim=claim):
                self.assert_rejected(
                    lambda record, claim=claim: record["claim_boundary"].__setitem__(claim, True)
                )

    def test_aether_provider_decision_must_remain_deferred(self) -> None:
        def mutate(record):
            for decision in record["provider_decisions"]:
                if decision["capability"] == "aether_provenance_projection":
                    decision["decision"] = "reuse_directly"
                    return
            self.fail("fixture lacks AETHER provider decision")

        self.assert_rejected(mutate)

    def test_mathsolve_routing_cannot_be_imported(self) -> None:
        def mutate(record):
            for decision in record["provider_decisions"]:
                if decision["capability"] == "mathsolve_mathematical_routing":
                    decision["decision"] = "generalize"
                    return
            self.fail("fixture lacks MATHSOLVE provider decision")

        self.assert_rejected(mutate)

    def test_duplicate_provider_capability_is_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["provider_decisions"].append(
                copy.deepcopy(record["provider_decisions"][0])
            )
        )

    def test_external_project_identity_cannot_leak_into_contract(self) -> None:
        self.assert_rejected(
            lambda record: record["authority"].__setitem__(
                "reference_note", "teraflop-ai/llm-data"
            )
        )


if __name__ == "__main__":
    unittest.main()
