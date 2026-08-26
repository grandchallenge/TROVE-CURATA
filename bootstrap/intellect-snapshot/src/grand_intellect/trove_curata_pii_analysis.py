"""Provider and baseline observation engines for TC-FIXTURE-002."""

from __future__ import annotations

import re
from typing import Any, Iterable

from .trove_curata_pii_contract import (
    AMBIGUITY_TERMS,
    BASELINE_RULES,
    PRESIDIO_RULES,
    PROVIDER_LOCK,
    SCHEMA_VERSION,
    TroveCurataPiiFixtureError,
    _require,
    canonical_json_bytes,
    make_observation,
    sha256_bytes,
    validate_observation,
)


def _regex_observations(
    text: str,
    rule_ids: Iterable[str],
    rules: dict[str, dict[str, str]],
    *,
    observer: str,
    provider_identity: dict[str, str],
    default_score: str,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for rule_id in sorted(rule_ids):
        spec = rules[rule_id]
        for match in re.finditer(spec["regex"], text):
            observations.append(
                make_observation(
                    observer=observer,
                    rule_id=rule_id,
                    entity_type=spec["entity_type"],
                    score=spec.get("score", default_score),
                    text=text,
                    start=match.start(),
                    end=match.end(),
                    provider_identity=provider_identity,
                )
            )
    return sorted(observations, key=_observation_sort_key)


def simulate_presidio_observations(text: str, rule_ids: Iterable[str], versions: dict[str, str] | None = None) -> list[dict[str, Any]]:
    identity = {
        "name": "presidio-analyzer",
        "version": (versions or PROVIDER_LOCK)["presidio-analyzer"],
        "adapter": "gcl_pattern_recognizer_v1",
    }
    return _regex_observations(
        text,
        rule_ids,
        PRESIDIO_RULES,
        observer="presidio",
        provider_identity=identity,
        default_score="0.500000",
    )


def analyze_with_presidio(text: str, language: str, rule_ids: Iterable[str], versions: dict[str, str]) -> list[dict[str, Any]]:
    """Run pinned Presidio PatternRecognizer instances without an NLP model download."""

    try:
        from presidio_analyzer import Pattern, PatternRecognizer
    except ImportError as exc:  # pragma: no cover - dedicated provider workflow
        raise TroveCurataPiiFixtureError(f"Presidio import failed: {exc}") from exc

    observations: list[dict[str, Any]] = []
    identity = {
        "name": "presidio-analyzer",
        "version": versions["presidio-analyzer"],
        "adapter": "gcl_pattern_recognizer_v1",
    }
    for rule_id in sorted(rule_ids):
        spec = PRESIDIO_RULES[rule_id]
        pattern = Pattern(name=rule_id, regex=spec["regex"], score=float(spec["score"]))
        recognizer = PatternRecognizer(
            supported_entity=spec["entity_type"],
            patterns=[pattern],
            supported_language=language,
            name=f"GCL::{rule_id}",
        )
        results = recognizer.analyze(text=text, entities=[spec["entity_type"]], nlp_artifacts=None)
        for result in results:
            observations.append(
                make_observation(
                    observer="presidio",
                    rule_id=rule_id,
                    entity_type=result.entity_type,
                    score=result.score,
                    text=text,
                    start=result.start,
                    end=result.end,
                    provider_identity=identity,
                )
            )
    return sorted(observations, key=_observation_sort_key)


def analyze_with_gcl_rules(text: str, rule_ids: Iterable[str]) -> list[dict[str, Any]]:
    rule_ids = list(rule_ids)
    observations = _regex_observations(
        text,
        [rule for rule in rule_ids if rule != "gcl-ambiguity-v1"],
        BASELINE_RULES,
        observer="gcl_rules",
        provider_identity={"name": "grand_intellect_rules", "version": SCHEMA_VERSION, "adapter": "python_re_v1"},
        default_score="1.000000",
    )
    if "gcl-ambiguity-v1" in rule_ids:
        for term in sorted(AMBIGUITY_TERMS):
            for match in re.finditer(rf"\b{re.escape(term)}\b", text):
                observations.append(
                    make_observation(
                        observer="gcl_rules",
                        rule_id="gcl-ambiguity-v1",
                        entity_type="AMBIGUOUS_NAME_LOCATION",
                        score="0.500000",
                        text=text,
                        start=match.start(),
                        end=match.end(),
                        provider_identity={"name": "grand_intellect_rules", "version": SCHEMA_VERSION, "adapter": "lexicon_v1"},
                    )
                )
    return sorted(observations, key=_observation_sort_key)


def _observation_sort_key(observation: dict[str, Any]) -> tuple[Any, ...]:
    return (
        observation["start_char"],
        observation["end_char"],
        observation["entity_type"],
        observation["rule_id"],
        observation["observer"],
    )


def overlapping_pairs(observations: list[dict[str, Any]]) -> list[list[str]]:
    pairs: list[list[str]] = []
    ordered = sorted(observations, key=_observation_sort_key)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if right["start_char"] >= left["end_char"]:
                break
            if left["start_char"] < right["end_char"] and right["start_char"] < left["end_char"]:
                pairs.append(sorted([left["observation_id"], right["observation_id"]]))
    return sorted(pairs)


def observation_set(observer: str, observations: list[dict[str, Any]], text: str) -> dict[str, Any]:
    for observation in observations:
        validate_observation(observation, text)
        _require(observation["observer"] == observer, "observation assigned to wrong set")
    overlaps = overlapping_pairs(observations)
    payload = {
        "observer": observer,
        "status": "rejected_overlap" if overlaps else "accepted",
        "observations": sorted(observations, key=_observation_sort_key),
        "overlap_pairs": overlaps,
    }
    return {**payload, "observation_digest": sha256_bytes(canonical_json_bytes(payload))}


def disagreement_record(provider_set: dict[str, Any], baseline_set: dict[str, Any]) -> dict[str, Any]:
    def signature(item: dict[str, Any]) -> tuple[str, int, int]:
        return item["entity_type"], item["start_char"], item["end_char"]

    provider = {signature(item) for item in provider_set["observations"]}
    baseline = {signature(item) for item in baseline_set["observations"]}
    provider_only = sorted([list(item) for item in provider - baseline])
    baseline_only = sorted([list(item) for item in baseline - provider])
    shared = sorted([list(item) for item in provider & baseline])
    present = bool(provider_only or baseline_only or provider_set["status"] != "accepted" or baseline_set["status"] != "accepted")
    payload = {
        "provider_only": provider_only,
        "baseline_only": baseline_only,
        "shared": shared,
        "provider_set_status": provider_set["status"],
        "baseline_set_status": baseline_set["status"],
        "disagreement_present": present,
    }
    return {**payload, "disagreement_digest": sha256_bytes(canonical_json_bytes(payload))}


def _entity_multiset(observations: list[dict[str, Any]]) -> list[str]:
    return sorted(observation["entity_type"] for observation in observations)
