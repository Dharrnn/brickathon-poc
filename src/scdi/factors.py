"""Configurable disruption-risk factor engine.

The risk model is *data*, not code: `factors.yml` declares the factors, their
weights, thresholds and human-readable reasons. `evaluate()` applies them
generically and returns the score **plus a per-factor breakdown** so every
outcome carries its reasoning. Weights/thresholds/actions can be changed, and
factors of an existing `kind` added, purely in the YAML; a brand-new `kind`
adds one evaluator function here (the only extension point).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path

import yaml

Inputs = dict[str, float | bool]


# --- Model data structures -------------------------------------------------
@dataclass(frozen=True)
class FactorSpec:
    id: str
    label: str
    kind: str
    weight: float
    params: dict
    reason: str


@dataclass(frozen=True)
class RiskModel:
    factors: list[FactorSpec]
    band_high: float
    band_medium: float
    actions: dict


@dataclass(frozen=True)
class FactorContribution:
    id: str
    label: str
    weight: float
    contribution: float  # normalized [0, 1]
    points: float        # weight * contribution
    reason: str


@dataclass(frozen=True)
class RiskResult:
    delay_score: float
    risk_band: str
    top_factor: str | None
    reasoning: str
    recommended_action: str
    slowdown_flag: bool
    breakdown: list[FactorContribution]


# --- Evaluator registry: kind -> (inputs, params) -> contribution in [0,1] --
EVALUATORS: dict[str, Callable[[Inputs, dict], float]] = {}


def evaluator(kind: str):
    def deco(fn: Callable[[Inputs, dict], float]):
        EVALUATORS[kind] = fn
        return fn
    return deco


@evaluator("slowdown")
def _slowdown(inputs: Inputs, params: dict) -> float:
    if not inputs.get("in_zone"):
        return 0.0
    slow = float(params.get("slow_sog_knots", 3.0))
    avg = max(float(inputs.get("avg_sog", 0.0)), 0.0)
    return 0.0 if avg >= slow else (slow - avg) / slow


@evaluator("weather_severity")
def _weather(inputs: Inputs, params: dict) -> float:
    # Weather only counts as port-disruption risk while the vessel is in a zone;
    # open-water transit in a storm is out of scope for this POC.
    if not inputs.get("in_zone"):
        return 0.0
    return max(0.0, min(float(inputs.get("weather_severity", 0.0)), 1.0))


@evaluator("in_zone")
def _in_zone(inputs: Inputs, params: dict) -> float:
    return 1.0 if inputs.get("in_zone") else 0.0


@evaluator("zone_congestion")
def _congestion(inputs: Inputs, params: dict) -> float:
    scale = float(params.get("congestion_scale", 5.0)) or 1.0
    return max(0.0, min(float(inputs.get("zone_slow_count", 0.0)) / scale, 1.0))


# --- Loading ---------------------------------------------------------------
def _parse(doc: dict) -> RiskModel:
    bands = doc.get("bands", {}) or {}
    factors = [
        FactorSpec(
            id=f["id"],
            label=f["label"],
            kind=f["kind"],
            weight=float(f["weight"]),
            params=f.get("params") or {},
            reason=f.get("reason", ""),
        )
        for f in doc.get("factors", [])
        if float(f.get("weight", 0)) > 0
    ]
    return RiskModel(
        factors=factors,
        band_high=float(bands.get("high", 60)),
        band_medium=float(bands.get("medium", 30)),
        actions=doc.get("actions") or {},
    )


@lru_cache(maxsize=1)
def default_model() -> RiskModel:
    text = resources.files("scdi").joinpath("factors.yml").read_text()
    return _parse(yaml.safe_load(text))


def load_model(path: str | Path | None = None) -> RiskModel:
    """Load the packaged default model, or a custom one from `path`."""
    if path is None:
        return default_model()
    return _parse(yaml.safe_load(Path(path).read_text()))


def model_from_dict(doc: dict) -> RiskModel:
    """Build a model from an in-memory dict (used by the MCP reweight tool)."""
    return _parse(doc)


# --- Scoring ---------------------------------------------------------------
def _band(model: RiskModel, s: float) -> str:
    if s >= model.band_high:
        return "high"
    if s >= model.band_medium:
        return "medium"
    return "low"


def _reason_text(spec: FactorSpec, inputs: Inputs, contribution: float, points: float) -> str:
    if not spec.reason:
        return spec.label
    ctx = {**spec.params, **inputs, "contribution": contribution, "points": points}
    try:
        return spec.reason.format(**ctx)
    except (KeyError, ValueError):
        return spec.label


def _action(model: RiskModel, band: str, top_id: str | None) -> str:
    rules = model.actions.get(band)
    if isinstance(rules, str):
        return rules
    if isinstance(rules, dict):
        return rules.get(top_id or "", rules.get("default", ""))
    # Sensible fallback if the model omits `actions`.
    return {
        "high": "Escalate: high delay risk — review schedule.",
        "medium": "Monitor; moderate delay risk.",
        "low": "No action; normal operations.",
    }[band]


def evaluate(inputs: Inputs, model: RiskModel | None = None) -> RiskResult:
    """Apply the factor model to one vessel/window's inputs, with reasoning."""
    model = model or default_model()
    breakdown: list[FactorContribution] = []
    total = 0.0
    for spec in model.factors:
        ev = EVALUATORS.get(spec.kind)
        if ev is None:
            continue
        c = max(0.0, min(ev(inputs, spec.params), 1.0))
        pts = round(c * spec.weight, 2)
        total += pts
        if c > 0:
            breakdown.append(
                FactorContribution(
                    spec.id, spec.label, spec.weight, round(c, 3), pts,
                    _reason_text(spec, inputs, c, pts),
                )
            )
    total = round(min(total, 100.0), 2)
    band = _band(model, total)
    active = sorted(breakdown, key=lambda b: b.points, reverse=True)
    top = active[0] if active else None
    reasoning = "; ".join(f"{b.label} ({b.points:g})" for b in active) or "No contributing factors"

    slow_param = next(
        (float(f.params.get("slow_sog_knots", 3.0)) for f in model.factors if f.kind == "slowdown"),
        3.0,
    )
    slowdown_flag = bool(inputs.get("in_zone")) and float(inputs.get("avg_sog", 0.0)) < slow_param

    return RiskResult(
        delay_score=total,
        risk_band=band,
        top_factor=top.label if top else None,
        reasoning=reasoning,
        recommended_action=_action(model, band, top.id if top else None),
        slowdown_flag=slowdown_flag,
        breakdown=active,
    )
