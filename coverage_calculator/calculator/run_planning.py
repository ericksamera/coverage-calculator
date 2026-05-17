# coverage_calculator/calculator/run_planning.py

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RunPlan:
    """Operational run-planning metrics from a theoretical sample capacity."""

    theoretical_samples_per_unit: float
    reserve_margin_pct: float
    adjusted_samples_per_unit: float
    recommended_samples_per_unit: int
    planning_samples: int
    units_required: int
    unused_capacity_samples: float


def calc_run_plan(
    *,
    samples_per_unit: float,
    planning_samples: int,
    reserve_margin_pct: float,
) -> RunPlan:
    """
    Convert theoretical sample capacity into an integer run plan.

    ``samples_per_unit`` is the theoretical sample capacity for one selected
    flow cell / SMRT Cell / run. The reserve margin reduces this capacity before
    rounding to an operational sample-loading recommendation.
    """

    theoretical = max(0.0, float(samples_per_unit))
    margin = max(0.0, min(95.0, float(reserve_margin_pct)))
    adjusted = theoretical * (1.0 - margin / 100.0)
    safe_samples = max(1, int(planning_samples))

    recommended = math.floor(adjusted) if adjusted >= 1.0 else 0
    if recommended > 0:
        units_required = math.ceil(safe_samples / recommended)
        unused_capacity = max(0.0, (units_required * recommended) - safe_samples)
    elif adjusted > 0:
        # The selected setup cannot fit one complete sample per unit at the
        # requested targets, but multiple units might still be used per sample.
        units_required = math.ceil(safe_samples / adjusted)
        unused_capacity = max(0.0, (units_required * adjusted) - safe_samples)
    else:
        units_required = 0
        unused_capacity = 0.0

    return RunPlan(
        theoretical_samples_per_unit=theoretical,
        reserve_margin_pct=margin,
        adjusted_samples_per_unit=adjusted,
        recommended_samples_per_unit=recommended,
        planning_samples=safe_samples,
        units_required=units_required,
        unused_capacity_samples=unused_capacity,
    )
