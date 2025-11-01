# coverage_calculator/calculator/effective_output.py

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EffectiveOutputStages:
    """Snapshot of effective-output steps used in the UI explainer."""

    o0: float  # base/platform output
    o1: float  # after instrument filtering
    o2: float  # after fragment/read overlap
    o3: float  # after library complexity (unique bases)
    o4: float  # after GC/sequence bias
    overlap_applies: bool
    redundancy: float  # r in (2L-F)/(2L) when overlap applies
    eff_fraction: float  # (1 - dup/100) * (on_target/100)


def compute_effective_output(
    *,
    base_output_bp: float,
    read_filter_loss_pct: float,
    apply_fragment_model: bool,
    fragment_size: Optional[int],
    read_length: Optional[int],
    apply_complexity: bool,
    apply_gc_bias: bool,
    gc_bias_pct: float,
    region_size_bp: int,
    duplication_pct: float,
    on_target_pct: float,
) -> EffectiveOutputStages:
    """
    Compute O0..O4 and the effective-yield fraction used by the calculator.

    Returns an EffectiveOutputStages dataclass for UI + math.
    """

    # O0: platform/base output
    o0 = float(max(0.0, base_output_bp))

    # O1: instrument filtering
    q = max(0.0, float(read_filter_loss_pct))
    o1 = o0 * (1.0 - q / 100.0)

    # O2: fragment/read overlap
    o2 = o1
    overlap_applies = False
    redundancy = 0.0
    if (
        apply_fragment_model
        and fragment_size
        and read_length
        and fragment_size > 0
        and read_length > 0
    ):
        if 2 * read_length > fragment_size:
            overlap_applies = True
            redundancy = (2 * read_length - fragment_size) / (2 * read_length)
            o2 = o1 * (1.0 - redundancy)

    # O3: library complexity (unique bases via Lander–Waterman)
    rsize = max(1, int(region_size_bp))
    if apply_complexity:
        o3 = rsize * (1.0 - math.exp(-o2 / rsize))
    else:
        o3 = o2

    # O4: GC / sequence bias
    if apply_gc_bias:
        b = max(0.0, float(gc_bias_pct))
        o4 = o3 * (1.0 - b / 100.0)
    else:
        o4 = o3

    # Effective-yield fraction from duplicates & on-target
    dup = max(0.0, float(duplication_pct))
    on_t = max(0.0, float(on_target_pct))
    eff_fraction = (1.0 - dup / 100.0) * (on_t / 100.0)
    eff_fraction = max(0.0, eff_fraction)

    return EffectiveOutputStages(
        o0=o0,
        o1=o1,
        o2=o2,
        o3=o3,
        o4=o4,
        overlap_applies=overlap_applies,
        redundancy=redundancy,
        eff_fraction=eff_fraction,
    )
