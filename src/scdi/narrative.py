"""Template natural-language summary — the local fallback for `ai_gen`.

On Databricks, notebooks/40_genie_summaries.sql regenerates the summary with an
AI SQL function for richer phrasing. Locally (and if AI functions are
unavailable in Free Edition) this template keeps every Gold row populated with an
operator-readable one-liner built from the factor reasoning.
"""

from __future__ import annotations


def build_summary(
    vessel_name: str,
    port_zone: str | None,
    risk_band: str,
    delay_score: float,
    reasoning: str,
    recommended_action: str,
) -> str:
    zone = port_zone or "open water"
    return (
        f"{vessel_name} in the {zone} zone is {risk_band} risk "
        f"(delay score {delay_score:.0f}/100). Drivers: {reasoning}. "
        f"{recommended_action}"
    )
