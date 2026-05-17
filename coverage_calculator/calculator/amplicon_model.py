# coverage_calculator/calculator/amplicon_model.py

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ReadUnitInfo:
    """Sequencing-unit metadata used for amplicon read-count planning."""

    label: str
    bases_per_unit: int
    inferred_from_platform: bool


@dataclass(frozen=True)
class AmpliconPlan:
    """Read-count planning metrics for amplicon panels."""

    read_unit_label: str
    bases_per_unit: int
    raw_read_units_per_sample: float
    usable_read_units_per_sample: float
    mean_read_units_per_amplicon: float
    imbalance_adjusted_read_units_per_amplicon: float
    target_usable_read_units_per_sample: float
    estimated_below_target_amplicons: float


def infer_read_unit_info(
    platform: Mapping[str, Any], *, fallback_unit_bp: int
) -> ReadUnitInfo:
    """
    Infer whether a platform should be planned in read pairs or reads.

    Structured platform metadata is preferred when present. For older platform
    definitions, this falls back to parsing names like "2x300", "2×150", or
    "1x100". If no read length can be inferred, one unit is treated as roughly
    one amplicon-length read so the calculator remains usable for long-read or
    variable-read platforms.
    """

    read_count = platform.get("read_count")
    read_length_bp = platform.get("read_length_bp")
    try:
        read_count_int = int(read_count) if read_count is not None else None
        read_length_int = int(read_length_bp) if read_length_bp is not None else None
    except (TypeError, ValueError):
        read_count_int = None
        read_length_int = None

    if (
        read_count_int
        and read_length_int
        and read_count_int > 0
        and read_length_int > 0
    ):
        label = "read pairs" if read_count_int == 2 else "reads"
        return ReadUnitInfo(
            label=label,
            bases_per_unit=read_count_int * read_length_int,
            inferred_from_platform=True,
        )

    name = str(platform.get("name", ""))
    match = re.search(r"(\d+)\s*[x×]\s*(\d+)", name)
    if match:
        n_reads, read_len = match.groups()
        read_count_int = int(n_reads)
        read_length_int = int(read_len)
        label = "read pairs" if read_count_int == 2 else "reads"
        return ReadUnitInfo(
            label=label,
            bases_per_unit=read_count_int * read_length_int,
            inferred_from_platform=True,
        )

    fallback = max(1, int(fallback_unit_bp))
    return ReadUnitInfo(
        label="reads",
        bases_per_unit=fallback,
        inferred_from_platform=False,
    )


def calc_amplicon_samples_per_flow_cell(
    *,
    output_bp: float,
    eff_fraction: float,
    num_amplicons: int,
    min_reads_per_amplicon: int,
    imbalance_factor: float,
    bases_per_read_unit: int,
) -> float:
    """Return samples supported using a read-units-per-amplicon target."""

    if output_bp <= 0 or eff_fraction <= 0:
        return 0.0

    target_usable_units = (
        max(1, int(num_amplicons))
        * max(1, int(min_reads_per_amplicon))
        * max(1.0, float(imbalance_factor))
    )
    raw_required_units = target_usable_units / eff_fraction
    raw_required_bp = raw_required_units * max(1, int(bases_per_read_unit))
    if raw_required_bp <= 0:
        return 0.0
    return output_bp / raw_required_bp


def calc_amplicon_supported_region_bp(
    *,
    output_bp: float,
    samples: int,
    eff_fraction: float,
    amplicon_size_bp: int,
    min_reads_per_amplicon: int,
    imbalance_factor: float,
    bases_per_read_unit: int,
) -> float:
    """Return the supported panel size in bp for a read-count target."""

    if output_bp <= 0 or samples <= 0 or eff_fraction <= 0:
        return 0.0

    usable_units_per_sample = (
        (output_bp / samples) / max(1, int(bases_per_read_unit)) * eff_fraction
    )
    supported_amplicons = usable_units_per_sample / (
        max(1, int(min_reads_per_amplicon)) * max(1.0, float(imbalance_factor))
    )
    return max(0.0, supported_amplicons * max(1, int(amplicon_size_bp)))


def calc_amplicon_plan(
    *,
    output_bp: float,
    samples: int,
    eff_fraction: float,
    num_amplicons: int,
    amplicon_size_bp: int,
    min_reads_per_amplicon: int,
    imbalance_factor: float,
    platform: Mapping[str, Any],
) -> AmpliconPlan:
    """Compute visible read-count metrics for the selected amplicon panel."""

    read_unit_info = infer_read_unit_info(
        platform, fallback_unit_bp=max(1, int(amplicon_size_bp))
    )
    bases_per_unit = max(1, int(read_unit_info.bases_per_unit))
    safe_samples = max(1, int(samples))
    safe_amplicons = max(1, int(num_amplicons))
    safe_min_reads = max(1, int(min_reads_per_amplicon))
    safe_imbalance = max(1.0, float(imbalance_factor))
    safe_eff = max(0.0, float(eff_fraction))

    raw_units_per_sample = (max(0.0, float(output_bp)) / safe_samples) / bases_per_unit
    usable_units_per_sample = raw_units_per_sample * safe_eff
    mean_units_per_amplicon = usable_units_per_sample / safe_amplicons
    adjusted_units_per_amplicon = mean_units_per_amplicon / safe_imbalance
    target_units_per_sample = safe_amplicons * safe_min_reads * safe_imbalance

    if adjusted_units_per_amplicon >= safe_min_reads:
        below_target_amplicons = 0.0
    else:
        shortfall_fraction = 1.0 - (adjusted_units_per_amplicon / safe_min_reads)
        below_target_amplicons = safe_amplicons * max(0.0, min(1.0, shortfall_fraction))

    return AmpliconPlan(
        read_unit_label=read_unit_info.label,
        bases_per_unit=bases_per_unit,
        raw_read_units_per_sample=raw_units_per_sample,
        usable_read_units_per_sample=usable_units_per_sample,
        mean_read_units_per_amplicon=mean_units_per_amplicon,
        imbalance_adjusted_read_units_per_amplicon=adjusted_units_per_amplicon,
        target_usable_read_units_per_sample=target_units_per_sample,
        estimated_below_target_amplicons=below_target_amplicons,
    )
