"""Plan validation and fragment-scoped transformation engines for TC-FIXTURE-003."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from .trove_curata_pii_analysis import (
    analyze_with_gcl_rules,
    disagreement_record,
    observation_set,
    simulate_presidio_observations,
)
from .trove_curata_pii_contract import normalize_text
from .trove_curata_transform_contract import (
    ALLOWED_OPERATORS,
    PREDECESSOR,
    TroveCurataTransformError,
    canonical_json_bytes,
    content_id,
    require,
    sha256_bytes,
)


def _predecessor_route(case: dict[str, Any], provider_set: dict[str, Any], baseline_set: dict[str, Any], disagreement: dict[str, Any]) -> str:
    if case["policy_state"] == "review_required":
        return "review_required"
    if provider_set["status"] != "accepted" or baseline_set["status"] != "accepted":
        return "review_required"
    if provider_set["observations"] or baseline_set["observations"] or disagreement["disagreement_present"]:
        return "review_required"
    return "observation_clear"


def predecessor_context(
    predecessor_manifest: dict[str, Any],
    predecessor_root: str | Path,
    predecessor_case_id: str,
) -> dict[str, Any]:
    cases = {case["case_id"]: case for case in predecessor_manifest["cases"]}
    require(predecessor_case_id in cases, f"unknown predecessor case: {predecessor_case_id}")
    case = cases[predecessor_case_id]
    root = Path(predecessor_root)
    text = normalize_text((root / case["path"]).read_text(encoding="utf-8"))
    require(text, f"empty predecessor source: {predecessor_case_id}")
    provider_observations = simulate_presidio_observations(text, case["provider_rules"])
    baseline_observations = analyze_with_gcl_rules(text, case["baseline_rules"])
    provider_set = observation_set("presidio", provider_observations, text)
    baseline_set = observation_set("gcl_rules", baseline_observations, text)
    disagreement = disagreement_record(provider_set, baseline_set)
    route = _predecessor_route(case, provider_set, baseline_set, disagreement)
    canonical_observation_digest = sha256_bytes(
        canonical_json_bytes(
            {
                "text_sha256": sha256_bytes(text.encode("utf-8")),
                "provider": provider_set,
                "baseline": baseline_set,
                "disagreement": disagreement,
                "route": route,
            }
        )
    )
    return {
        "predecessor": PREDECESSOR,
        "case": case,
        "text": text,
        "text_sha256": sha256_bytes(text.encode("utf-8")),
        "canonical_observation_digest": canonical_observation_digest,
        "provider_observation_set": provider_set,
        "baseline_observation_set": baseline_set,
        "disagreement": disagreement,
        "route": route,
    }


def _validate_operator(operation: dict[str, Any], matched_text: str) -> str | None:
    operator = operation["operator"]
    parameters = operation["parameters"]
    if operator not in ALLOWED_OPERATORS:
        return "rejected_operator"
    if operator == "replace":
        if set(parameters) != {"new_value"} or not isinstance(parameters["new_value"], str):
            return "rejected_parameters"
    elif operator == "mask":
        if set(parameters) != {"chars_to_mask", "masking_char", "from_end"}:
            return "rejected_parameters"
        if not isinstance(parameters["chars_to_mask"], int) or not 1 <= parameters["chars_to_mask"] <= len(matched_text):
            return "rejected_parameters"
        if not isinstance(parameters["masking_char"], str) or len(parameters["masking_char"]) != 1:
            return "rejected_parameters"
        if not isinstance(parameters["from_end"], bool):
            return "rejected_parameters"
    elif operator == "keep" and parameters:
        return "rejected_parameters"
    return None


def evaluate_plan(case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    binding = {
        "source_sha256": case["source_sha256"],
        "canonical_observation_digest": case["canonical_observation_digest"],
        "operations": deepcopy(case["operations"]),
        "plan_state": case["plan_state"],
        "plan_authority": "grandchallenge",
    }
    plan_id = content_id("curata-transformation-plan", binding)
    if case["plan_state"] == "withheld":
        require(not case["operations"], "withheld plan must not contain operations")
        return {"plan_id": plan_id, "status": "withheld", "binding": binding, "resolved_operations": []}
    if case["source_sha256"] != context["text_sha256"]:
        return {"plan_id": plan_id, "status": "rejected_stale_source", "binding": binding, "resolved_operations": []}
    if case["canonical_observation_digest"] != context["canonical_observation_digest"]:
        return {"plan_id": plan_id, "status": "rejected_observation_digest", "binding": binding, "resolved_operations": []}

    observations = {item["observation_id"]: item for item in context["provider_observation_set"]["observations"]}
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for operation in case["operations"]:
        observation_id = operation["observation_id"]
        if observation_id in seen:
            return {"plan_id": plan_id, "status": "rejected_duplicate_observation", "binding": binding, "resolved_operations": []}
        seen.add(observation_id)
        observation = observations.get(observation_id)
        if observation is None:
            return {"plan_id": plan_id, "status": "rejected_observation_identity", "binding": binding, "resolved_operations": []}
        if (
            operation["entity_type"] != observation["entity_type"]
            or operation["start_char"] != observation["start_char"]
            or operation["end_char"] != observation["end_char"]
        ):
            return {"plan_id": plan_id, "status": "rejected_observation_identity", "binding": binding, "resolved_operations": []}
        operator_error = _validate_operator(operation, observation["matched_text"])
        if operator_error:
            return {"plan_id": plan_id, "status": operator_error, "binding": binding, "resolved_operations": []}
        resolved.append({**deepcopy(operation), "matched_text": observation["matched_text"]})

    resolved.sort(key=lambda item: (item["start_char"], item["end_char"], item["observation_id"]))
    for left, right in zip(resolved, resolved[1:]):
        if right["start_char"] < left["end_char"]:
            return {"plan_id": plan_id, "status": "rejected_overlap", "binding": binding, "resolved_operations": []}
    return {"plan_id": plan_id, "status": "accepted", "binding": binding, "resolved_operations": resolved}


def apply_baseline_fragment(matched_text: str, entity_type: str, operator: str, parameters: dict[str, Any]) -> str:
    del entity_type
    if operator == "replace":
        return parameters["new_value"]
    if operator == "keep":
        return matched_text
    if operator == "mask":
        count = parameters["chars_to_mask"]
        masked = parameters["masking_char"] * count
        if parameters["from_end"]:
            return matched_text[:-count] + masked
        return masked + matched_text[count:]
    raise TroveCurataTransformError(f"unsupported baseline operator: {operator}")


def simulate_provider_fragment(matched_text: str, entity_type: str, operator: str, parameters: dict[str, Any]) -> str:
    if operator == "replace":
        return parameters["new_value"] or f"<{entity_type}>"
    return apply_baseline_fragment(matched_text, entity_type, operator, parameters)


def transform_fragment_with_presidio(
    matched_text: str,
    entity_type: str,
    operator: str,
    parameters: dict[str, Any],
    versions: dict[str, str],
) -> str:
    try:
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig, RecognizerResult
    except ImportError as exc:  # pragma: no cover - dedicated provider workflow
        raise TroveCurataTransformError(f"Presidio Anonymizer import failed: {exc}") from exc
    require(versions["presidio-anonymizer"] == "2.2.363", "unexpected Presidio Anonymizer version")
    result = AnonymizerEngine().anonymize(
        text=matched_text,
        analyzer_results=[RecognizerResult(entity_type=entity_type, start=0, end=len(matched_text), score=1.0)],
        operators={entity_type: OperatorConfig(operator, parameters)},
    )
    require(isinstance(result.text, str), "Presidio returned a non-string fragment")
    return result.text


def assemble_output(
    text: str,
    resolved_operations: list[dict[str, Any]],
    transform_fragment: Callable[[str, str, str, dict[str, Any]], str],
) -> tuple[str, list[dict[str, Any]], list[str]]:
    output_parts: list[str] = []
    operation_results: list[dict[str, Any]] = []
    source_gaps: list[str] = []
    cursor = 0
    for operation in resolved_operations:
        gap = text[cursor : operation["start_char"]]
        source_gaps.append(gap)
        output_parts.append(gap)
        fragment = transform_fragment(
            operation["matched_text"],
            operation["entity_type"],
            operation["operator"],
            operation["parameters"],
        )
        output_parts.append(fragment)
        operation_results.append(
            {
                "observation_id": operation["observation_id"],
                "entity_type": operation["entity_type"],
                "start_char": operation["start_char"],
                "end_char": operation["end_char"],
                "operator": operation["operator"],
                "parameters": deepcopy(operation["parameters"]),
                "source_fragment_sha256": sha256_bytes(operation["matched_text"].encode("utf-8")),
                "output_fragment": fragment,
                "output_fragment_sha256": sha256_bytes(fragment.encode("utf-8")),
            }
        )
        cursor = operation["end_char"]
    tail = text[cursor:]
    source_gaps.append(tail)
    output_parts.append(tail)
    return "".join(output_parts), operation_results, source_gaps


def residual_audit(text: str, baseline_rules: list[str]) -> dict[str, Any]:
    observations = analyze_with_gcl_rules(text, baseline_rules)
    group = observation_set("gcl_rules", observations, text)
    payload = {
        "observer": "gcl_rules",
        "observation_digest": group["observation_digest"],
        "observation_count": len(group["observations"]),
        "observations": group["observations"],
        "provider_may_suppress_residuals": False,
    }
    return {**payload, "residual_audit_id": content_id("curata-residual-audit", payload)}
