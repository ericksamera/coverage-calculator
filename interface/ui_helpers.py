# interface/ui_helpers.py

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Dict, Iterable, Optional, Tuple
import html
import re

import streamlit as st

from coverage_calculator.calculator.amplicon_model import AmpliconPlan
from coverage_calculator.calculator.run_planning import RunPlan, calc_run_plan
from coverage_calculator.utils.unit_parser import (
    format_region_size,
    parse_region_size,
)

_DEFAULT_PLATFORM_ID = "MISEQ_I100_25M_PE300"


# ----------------------------
# Results metric + warnings
# ----------------------------
def _hero_value(label: str, value: str) -> str:
    """Add obvious units to the large right-rail result when helpful."""

    if "samples per" in label.lower() and "sample" not in value.lower():
        return f"{value} samples"
    return value


def _result_warnings(
    *,
    variable: str,
    result,
    total_bp: float,
    num_amplicons: Optional[int],
) -> list[tuple[str, str]]:
    """Return warning/error messages for the current result state."""

    messages: list[tuple[str, str]] = []
    if (
        variable == "Samples per flow cell"
        and isinstance(result, (int, float))
        and result < 1
    ):
        messages.append(
            ("warning", "Sequencing output is too low for even one sample.")
        )
    if total_bp < 1_000_000:
        messages.append(("error", "Effective sequencing output is extremely low."))
    if (
        variable == "Samples per flow cell"
        and num_amplicons is not None
        and num_amplicons > 100_000
    ):
        messages.append(
            (
                "warning",
                "Number of amplicons is very high. Is your region size correct?",
            )
        )
    return messages


def _show_result_warnings(
    warning_placeholder,
    *,
    variable: str,
    result,
    total_bp: float,
    num_amplicons: Optional[int],
) -> None:
    messages = _result_warnings(
        variable=variable,
        result=result,
        total_bp=total_bp,
        num_amplicons=num_amplicons,
    )
    if not messages:
        warning_placeholder.empty()
        return

    with warning_placeholder.container():
        for severity, message in messages:
            if severity == "error":
                st.error(message)
            else:
                st.warning(message)


def show_results_ui(
    result_placeholder,
    warning_placeholder,
    variable: str,
    result,
    label: str,
    value: str,
    delta: str,
    total_bp: float,
    num_amplicons: Optional[int] = None,
) -> None:
    """
    Shows the result metric and any relevant warnings, with a border around the metric.
    """
    with result_placeholder:
        with st.container(border=True):
            st.metric(label=label, value=value, delta=delta, delta_color="off")

    _show_result_warnings(
        warning_placeholder,
        variable=variable,
        result=result,
        total_bp=total_bp,
        num_amplicons=num_amplicons,
    )


def show_results_rail_ui(
    result_placeholder,
    warning_placeholder,
    variable: str,
    result,
    label: str,
    value: str,
    delta: str,
    total_bp: float,
    *,
    num_amplicons: Optional[int] = None,
    supporting_metrics: Optional[Iterable[tuple[str, str]]] = None,
    summary_rows: Optional[Iterable[tuple[str, str]]] = None,
) -> None:
    """Render the result in a dedicated right-side rail."""

    safe_label = html.escape(label)
    safe_value = html.escape(_hero_value(label, value))
    safe_delta = html.escape(delta)

    with result_placeholder.container():
        with st.container(border=True):
            st.markdown("**Result**")
            st.caption("Live estimate based on your inputs.")

        with st.container(border=True):
            st.markdown("**Run summary**")
            for row_label, row_value in list(summary_rows or []):
                st.markdown(
                    """
<div class="seqcalc-summary-row">
  <span class="seqcalc-summary-label">{label}</span>
  <span class="seqcalc-summary-value">{value}</span>
</div>
""".format(
                        label=html.escape(str(row_label)),
                        value=html.escape(str(row_value)),
                    ),
                    unsafe_allow_html=True,
                )

        with st.container(border=True):
            st.markdown(
                f"""
<div class="seqcalc-result-hero">
  <div class="seqcalc-result-label">{safe_label}</div>
  <div class="seqcalc-result-value">{safe_value}</div>
  <div class="seqcalc-result-delta">{safe_delta}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.divider()

            metrics = list(supporting_metrics or [])
            for metric_label, metric_value in metrics:
                st.markdown(
                    """
<div class="seqcalc-metric-row">
  <div class="seqcalc-metric-label">{label}</div>
  <div class="seqcalc-metric-value">{value}</div>
</div>
""".format(
                        label=html.escape(str(metric_label)),
                        value=html.escape(str(metric_value)),
                    ),
                    unsafe_allow_html=True,
                )

        st.info(
            "Results reflect nominal platform output adjusted for runtime and modifiers. "
            "Open advanced modeling options to account for additional assumptions."
        )

    _show_result_warnings(
        warning_placeholder,
        variable=variable,
        result=result,
        total_bp=total_bp,
        num_amplicons=num_amplicons,
    )


def run_unit_labels(platform: Dict[str, Any]) -> Tuple[str, str]:
    """Return singular/plural labels for the selected sequencing unit."""

    name = str(platform.get("name", "")).lower()
    if "pacbio" in name and "run" in name:
        return "run", "runs"
    if "smrt cell" in name:
        return "SMRT Cell", "SMRT Cells"
    return "flow cell", "flow cells"


def run_planning_ui(
    *,
    params,
    samples_per_unit: float,
    default_samples_to_plan: int,
    platform: Dict[str, Any],
    show_sample_input: bool = True,
    planning_samples_override: Optional[int] = None,
    compact: bool = False,
) -> Tuple[RunPlan, int, float]:
    """Display operational run-planning metrics from theoretical capacity."""

    singular_unit, plural_unit = run_unit_labels(platform)
    if planning_samples_override is not None:
        default_planning_samples = max(1, int(planning_samples_override))
    else:
        default_planning_samples = max(
            1, int(params.get("planning_samples", default_samples_to_plan))
        )
    default_reserve_margin = float(params.get("reserve_margin_pct", 15.0))

    def reserve_margin_input() -> float:
        common_kwargs = {
            "label": "Planning reserve margin (%)",
            "min_value": 0.0,
            "max_value": 50.0,
            "value": max(0.0, min(50.0, default_reserve_margin)),
            "step": 1.0,
            "help": (
                "Capacity held back for yield variation, pooling imbalance, and "
                "library QC uncertainty."
            ),
        }
        if compact:
            return float(st.number_input(**common_kwargs, format="%.1f"))
        return float(st.slider(**common_kwargs))

    with st.container(border=True):
        st.subheader("Operational run planning", anchor=False)
        if show_sample_input:
            col_samples, col_reserve = st.columns(2)
            with col_samples:
                planning_samples = st.number_input(
                    "Samples to plan",
                    min_value=1,
                    value=default_planning_samples,
                    step=1,
                    help=(
                        "Total number of samples you intend to load across one or more "
                        f"{plural_unit}."
                    ),
                )
            with col_reserve:
                reserve_margin_pct = reserve_margin_input()
        else:
            planning_samples = default_planning_samples
            st.caption(
                f"Planning {planning_samples:,} samples from the main Samples input."
            )
            reserve_margin_pct = reserve_margin_input()

        plan = calc_run_plan(
            samples_per_unit=float(samples_per_unit),
            planning_samples=int(planning_samples),
            reserve_margin_pct=float(reserve_margin_pct),
        )

        if compact:
            st.metric(
                f"Theoretical samples/{singular_unit}",
                f"{plan.theoretical_samples_per_unit:.1f}",
                delta_color="off",
            )
            recommended_value = (
                f"{plan.recommended_samples_per_unit:d}"
                if plan.recommended_samples_per_unit > 0
                else f"{plan.adjusted_samples_per_unit:.2f}"
            )
            st.metric(
                f"Recommended samples/{singular_unit}",
                recommended_value,
                delta=f"{plan.reserve_margin_pct:.0f}% reserve",
                delta_color="off",
            )
            required_label = (
                f"{plural_unit} required"
                if plural_unit.startswith("SMRT")
                else f"{plural_unit[:1].upper()}{plural_unit[1:]} required"
            )
            st.metric(
                required_label,
                "—" if plan.units_required <= 0 else f"{plan.units_required:d}",
                delta_color="off",
            )
            st.metric(
                "Unused recommended capacity",
                f"{plan.unused_capacity_samples:.1f} samples",
                delta_color="off",
            )

            if plan.theoretical_samples_per_unit < 1:
                st.warning(
                    f"The selected setup has less than one theoretical sample of capacity per {singular_unit}. "
                    "Consider a higher-output configuration or lower per-sample target."
                )
            elif plan.recommended_samples_per_unit < 1:
                st.warning(
                    f"After the reserve margin, less than one sample fits per {singular_unit}."
                )

            st.caption(
                "Reserve is applied to theoretical capacity; recommended loading is "
                "rounded down and required units are rounded up."
            )
            return plan, int(planning_samples), float(reserve_margin_pct)

        col_theory, col_recommended, col_units, col_unused = st.columns(4)
        with col_theory:
            st.metric(
                f"Theoretical samples/{singular_unit}",
                f"{plan.theoretical_samples_per_unit:.1f}",
                delta_color="off",
            )
        with col_recommended:
            recommended_value = (
                f"{plan.recommended_samples_per_unit:d}"
                if plan.recommended_samples_per_unit > 0
                else f"{plan.adjusted_samples_per_unit:.2f}"
            )
            st.metric(
                f"Recommended samples/{singular_unit}",
                recommended_value,
                delta=f"{plan.reserve_margin_pct:.0f}% reserve",
                delta_color="off",
            )
        with col_units:
            required_label = (
                f"{plural_unit} required"
                if plural_unit.startswith("SMRT")
                else f"{plural_unit[:1].upper()}{plural_unit[1:]} required"
            )
            st.metric(
                required_label,
                "—" if plan.units_required <= 0 else f"{plan.units_required:d}",
                delta_color="off",
            )
        with col_unused:
            st.metric(
                "Unused recommended capacity",
                f"{plan.unused_capacity_samples:.1f} samples",
                delta_color="off",
            )

        if plan.theoretical_samples_per_unit < 1:
            st.warning(
                f"The selected setup has less than one theoretical sample of capacity per {singular_unit}. "
                "Consider a higher-output configuration or lower per-sample target."
            )
        elif plan.recommended_samples_per_unit < 1:
            st.warning(
                f"After the reserve margin, less than one sample fits per {singular_unit}."
            )

        st.caption(
            "Recommended loading applies the reserve margin to theoretical capacity and "
            "rounds down; required units are rounded up for purchasing/run planning."
        )

    return plan, int(planning_samples), float(reserve_margin_pct)


# ----------------------------
# Core UI helpers
# ----------------------------
def dedup_on_target_ui(
    preset_values,
    params,
    *,
    bordered: bool = False,
    show_preset_values: bool = False,
) -> Tuple[float, float]:
    """
    Shows duplication and on-target controls.

    When ``show_preset_values`` is true, preset-derived values are displayed as
    disabled inputs so the layout remains stable across Custom and preset modes.
    """

    using_preset = preset_values is not None
    if using_preset:
        duplication_default = float(preset_values.duplication_pct)
        on_target_default = max(1, int(preset_values.on_target_pct))
    else:
        duplication_default = float(params["duplication"])
        on_target_default = max(1, int(params["on_target"]))

    if using_preset and not show_preset_values:
        return duplication_default, float(on_target_default)

    def duplication_input() -> float:
        return float(
            st.number_input(
                "Duplication (%)",
                min_value=0.0,
                max_value=50.0,
                value=max(0.0, min(50.0, duplication_default)),
                step=0.5,
                format="%.2f",
                disabled=using_preset,
                help=(
                    "Estimated percent of duplicate reads "
                    "(remove PCR/sequencing duplicates)."
                ),
            )
        )

    def on_target_input() -> float:
        return float(
            st.number_input(
                "On-target (%)",
                min_value=1,
                max_value=100,
                value=max(1, min(100, on_target_default)),
                step=1,
                disabled=using_preset,
                help=(
                    "Fraction of sequenced reads mapping to the intended region/target. "
                    "Must be ≥ 1%."
                ),
            )
        )

    col_dup, col_target = st.columns(2)
    with col_dup:
        container_context = st.container(border=True) if bordered else nullcontext()
        with container_context:
            duplication = duplication_input()
    with col_target:
        container_context = st.container(border=True) if bordered else nullcontext()
        with container_context:
            on_target = on_target_input()

    if using_preset and show_preset_values:
        st.caption(
            "Duplication and on-target values are provided by the selected preset."
        )

    return duplication, on_target


def advanced_options_ui(
    coverage_mode: str,
    params,
    platform_id=None,
    platform=None,
):
    """
    Advanced modeling options expander.

    Returns:
      apply_gc_bias, gc_bias_percent, apply_fragment_model,
      fragment_size, read_length, read_filter_loss
    """
    with st.expander("Advanced Modeling Options", expanded=False):
        apply_gc_bias = st.checkbox(
            "Apply GC/sequence bias correction",
            value=params["apply_gc_bias"],
            help="Models loss of usable data from GC or other sequence content bias.",
        )
        apply_fragment_model = st.checkbox(
            "Adjust for fragment/read length overlap",
            value=params["apply_fragment_model"],
            help=(
                "Subtracts overlapping bases when paired-end reads extend beyond the "
                "fragment."
            ),
        )

        # --- Infer defaults from platform run (e.g. 'MiSeq i100 5M (2x300)') ---
        default_fragment_size = params.get("fragment_size", 300)
        default_read_length = params.get("read_length", 150)

        if platform is not None:
            read_length_bp = platform.get("read_length_bp")
            if isinstance(read_length_bp, int) and read_length_bp > 0:
                default_read_length = read_length_bp
                # Simple neutral default: fragment ≈ 2 × read length
                default_fragment_size = read_length_bp * 2
            else:
                name = str(platform.get("name", ""))
                # Grab patterns like "2x300", "2×300", "2x150", "1x100"
                m = re.search(r"(\d+)\s*[x×]\s*(\d+)", name)
                if m:
                    _n_reads, rl = m.groups()
                    try:
                        rl_int = int(rl)
                        default_read_length = rl_int
                        # Simple neutral default: fragment ≈ 2 × read length
                        default_fragment_size = rl_int * 2
                    except ValueError:
                        # Fall back to params / hard-coded defaults
                        pass

        read_filter_loss = st.slider(
            "Instrument Q-score/quality filtering loss (%)",
            min_value=0.0,
            max_value=20.0,
            value=params.get("read_filter_loss", 5.0),
            step=0.5,
            help=(
                "Percent of reads lost to instrument filtering (fail QC/basecalling). "
                "Typical: 3–7%."
            ),
        )

        if apply_fragment_model:
            fragment_size = st.number_input(
                "Fragment size (bp)",
                min_value=50,
                value=int(default_fragment_size),
                help="Average size of sequencing fragments after library prep.",
            )
            read_length = st.number_input(
                "Read length (bp)",
                min_value=50,
                value=int(default_read_length),
                help="Length of each sequencing read (e.g. 150 for PE150).",
            )
        else:
            fragment_size = None
            read_length = None

        if apply_gc_bias:
            gc_bias_percent = st.slider(
                "Bias loss (%)",
                0.0,
                20.0,
                params["gc_bias_percent"],
                help="Fraction of data lost due to GC or other sequence content bias.",
            )
        else:
            gc_bias_percent = 0.0

    return (
        apply_gc_bias,
        gc_bias_percent,
        apply_fragment_model,
        fragment_size,
        read_length,
        read_filter_loss,
    )


def preset_select_ui(coverage_mode: str, params, GENOME_WIDE_PRESETS, TARGETED_PRESETS):
    """
    Shows the preset selectbox for protocols.
    Returns: (preset_label, preset_values, active_presets)
    """
    if coverage_mode == "Genome-wide":
        active_presets = GENOME_WIDE_PRESETS
    else:
        active_presets = TARGETED_PRESETS

    preset_label_list = ["Custom"] + [
        preset.label for preset in active_presets.values()
    ]
    desired_label = params.get("preset", "Custom")
    # Backward compatibility for saved configurations that used older
    # targeted marker-amplicon preset names.
    legacy_preset_labels = {
        "Metagenomics": "16S / ITS / marker amplicon",
        "16S / marker amplicon": "16S / ITS / marker amplicon",
    }
    desired_label = legacy_preset_labels.get(desired_label, desired_label)
    try:
        default_index = preset_label_list.index(desired_label)
    except ValueError:
        default_index = 0

    preset_label = st.selectbox(
        "Protocol Preset",
        preset_label_list,
        index=default_index,
        help=(
            "Select a common protocol to auto-fill recommended parameters like region "
            "size, duplication, and on-target rate."
        ),
    )
    if preset_label != "Custom":
        preset_key = next(
            (
                key
                for key, preset in active_presets.items()
                if preset.label == preset_label
            ),
            None,
        )
        if preset_key is None:
            st.error("Internal error: selected preset not found.")
            st.stop()
        preset_values = active_presets[preset_key]
    else:
        preset_values = None

    return preset_label, preset_values, active_presets


def _ordered_unique(values: Iterable[str]) -> list[str]:
    """Return unique values in first-seen order, omitting empty strings."""
    seen = set()
    unique_values = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def _select_index(options: list[str], desired: str) -> int:
    try:
        return options.index(desired)
    except ValueError:
        return 0


def _platform_field(platform: Dict[str, Any], field: str) -> str:
    fallback_values = {
        "technology": "Other",
        "instrument": "Other",
        "flow_cell": "Default",
        "read_length": "Default",
    }
    value = platform.get(field)
    if value is None or value == "":
        return fallback_values.get(field, "Default")
    return str(value)


def _filter_platforms(
    platforms: Dict[str, Dict[str, Any]], **criteria: str
) -> Dict[str, Dict[str, Any]]:
    return {
        pid: platform
        for pid, platform in platforms.items()
        if all(
            _platform_field(platform, field) == value
            for field, value in criteria.items()
        )
    }


def _resolve_default_platform_id(
    params, platform_ids: list[str], platform_names: list[str]
) -> str:
    requested_platform = params.get("platform")
    if requested_platform in platform_ids:
        return requested_platform

    for pid, pname in zip(platform_ids, platform_names):
        if requested_platform == pname:
            return pid

    if _DEFAULT_PLATFORM_ID in platform_ids:
        return _DEFAULT_PLATFORM_ID

    return platform_ids[0]


def _has_grouped_platform_metadata(platforms: Dict[str, Dict[str, Any]]) -> bool:
    required_fields = ("technology", "instrument", "flow_cell", "read_length")
    return all(
        all(platform.get(field) for field in required_fields)
        for platform in platforms.values()
    )


def _platform_output_ui(platform: Dict[str, Any], runtime_hr: int) -> Tuple[float, int]:
    base_output_bp = platform["output_bp"]
    output_bp = base_output_bp

    # Prefer config-driven rate when present; works for MinION and similar platforms.
    bp_per_min = int(platform.get("bp_per_minute") or 0)

    if bp_per_min > 0:
        runtime_hr = st.slider(
            "Runtime (hrs)",
            0,
            72,
            runtime_hr,
            help="For ONT MinION or other runtime-scaled platforms.",
        )
        output_bp = bp_per_min * runtime_hr * 60
        st.caption(
            f"Estimated output: {format_region_size(int(output_bp))} based on runtime."
        )
    else:
        st.caption(f"Nominal output: {format_region_size(int(base_output_bp))}.")

    return output_bp, runtime_hr


def platform_selector_ui(
    params,
    PLATFORM_CONFIG,
    *,
    compact: bool = False,
    cascade: bool = False,
    bordered: bool = True,
):
    platform_ids = list(PLATFORM_CONFIG.keys())
    if not platform_ids:
        st.error("No sequencing platforms are configured.")
        st.stop()

    platform_names = [PLATFORM_CONFIG[pid]["name"] for pid in platform_ids]
    default_platform_id = _resolve_default_platform_id(
        params, platform_ids, platform_names
    )
    runtime_hr = params.get("runtime_hr", 48)

    if cascade and _has_grouped_platform_metadata(PLATFORM_CONFIG):
        default_platform = PLATFORM_CONFIG[default_platform_id]

        container_context = st.container(border=bordered) if bordered else nullcontext()
        with container_context:
            if bordered:
                st.markdown("**Sequencing platform**")
            col_tech, col_instrument, col_config = st.columns(
                [0.95, 1.05, 1.25], gap="small"
            )

            with col_tech:
                technology_options = _ordered_unique(
                    _platform_field(platform, "technology")
                    for platform in PLATFORM_CONFIG.values()
                )
                selected_technology = st.selectbox(
                    "Technology",
                    options=technology_options,
                    index=_select_index(
                        technology_options,
                        _platform_field(default_platform, "technology"),
                    ),
                    help="Sequencing chemistry / platform family.",
                )

            technology_platforms = _filter_platforms(
                PLATFORM_CONFIG, technology=selected_technology
            )

            with col_instrument:
                instrument_options = _ordered_unique(
                    _platform_field(platform, "instrument")
                    for platform in technology_platforms.values()
                )
                selected_instrument = st.selectbox(
                    "Instrument",
                    options=instrument_options,
                    index=_select_index(
                        instrument_options,
                        _platform_field(default_platform, "instrument"),
                    ),
                    help="Instrument model available for the selected technology.",
                )

            instrument_platforms = _filter_platforms(
                technology_platforms, instrument=selected_instrument
            )

            def platform_config_label(platform: Dict[str, Any]) -> str:
                flow_cell = _platform_field(platform, "flow_cell")
                read_length = _platform_field(platform, "read_length")
                if read_length and read_length.lower() not in flow_cell.lower():
                    return f"{flow_cell} · {read_length}"
                return flow_cell

            with col_config:
                config_options = _ordered_unique(
                    platform_config_label(platform)
                    for platform in instrument_platforms.values()
                )
                selected_config = st.selectbox(
                    "Flow cell / read length",
                    options=config_options,
                    index=_select_index(
                        config_options,
                        platform_config_label(default_platform),
                    ),
                    help="Only configurations valid for the selected instrument are shown.",
                )

            matching_platforms = {
                pid: platform
                for pid, platform in instrument_platforms.items()
                if platform_config_label(platform) == selected_config
            }
            if not matching_platforms:
                st.error("No platform configuration matches the selected options.")
                st.stop()

            if len(matching_platforms) == 1:
                platform_id, platform = next(iter(matching_platforms.items()))
            else:
                matching_ids = list(matching_platforms.keys())
                matching_names = [
                    matching_platforms[pid]["name"] for pid in matching_ids
                ]
                selected_name = st.selectbox(
                    "Configuration",
                    options=matching_names,
                    index=_select_index(matching_ids, default_platform_id),
                    help="Multiple platform definitions matched; choose the exact configuration.",
                )
                platform_id = matching_ids[matching_names.index(selected_name)]
                platform = PLATFORM_CONFIG[platform_id]

            st.caption(f"Selected configuration: {platform['name']}.")
            output_bp, runtime_hr = _platform_output_ui(platform, runtime_hr)
        return platform_id, platform, output_bp, runtime_hr

    if compact:
        platform_idx = platform_ids.index(default_platform_id)
        container_context = st.container(border=bordered) if bordered else nullcontext()
        with container_context:
            selected_name = st.selectbox(
                "Sequencing Platform",
                options=platform_names,
                index=platform_idx,
                help="Sequencing instrument / flow-cell configuration.",
            )
            platform_id = platform_ids[platform_names.index(selected_name)]
            platform = PLATFORM_CONFIG[platform_id]
            output_bp, runtime_hr = _platform_output_ui(platform, runtime_hr)
        return platform_id, platform, output_bp, runtime_hr

    if not _has_grouped_platform_metadata(PLATFORM_CONFIG):
        platform_idx = platform_ids.index(default_platform_id)
        selected_name = st.selectbox(
            "Sequencing Platform",
            options=platform_names,
            index=platform_idx,
        )
        platform_id = platform_ids[platform_names.index(selected_name)]
        platform = PLATFORM_CONFIG[platform_id]
        output_bp, runtime_hr = _platform_output_ui(platform, runtime_hr)
        return platform_id, platform, output_bp, runtime_hr

    default_platform = PLATFORM_CONFIG[default_platform_id]

    container_context = st.container(border=bordered) if bordered else nullcontext()
    with container_context:
        if bordered:
            st.subheader("Sequencing platform", anchor=False)
        col_tech, col_instrument, col_flow_cell, col_read_length = st.columns(4)

        with col_tech:
            technology_options = _ordered_unique(
                _platform_field(platform, "technology")
                for platform in PLATFORM_CONFIG.values()
            )
            selected_technology = st.selectbox(
                "Technology",
                options=technology_options,
                index=_select_index(
                    technology_options,
                    _platform_field(default_platform, "technology"),
                ),
                help="Sequencing chemistry / platform family.",
            )

        technology_platforms = _filter_platforms(
            PLATFORM_CONFIG, technology=selected_technology
        )

        with col_instrument:
            instrument_options = _ordered_unique(
                _platform_field(platform, "instrument")
                for platform in technology_platforms.values()
            )
            selected_instrument = st.selectbox(
                "Instrument",
                options=instrument_options,
                index=_select_index(
                    instrument_options,
                    _platform_field(default_platform, "instrument"),
                ),
                help="Instrument model available for the selected technology.",
            )

        instrument_platforms = _filter_platforms(
            technology_platforms, instrument=selected_instrument
        )

        with col_flow_cell:
            flow_cell_options = _ordered_unique(
                _platform_field(platform, "flow_cell")
                for platform in instrument_platforms.values()
            )
            selected_flow_cell = st.selectbox(
                "Flow cell / kit",
                options=flow_cell_options,
                index=_select_index(
                    flow_cell_options,
                    _platform_field(default_platform, "flow_cell"),
                ),
                help="Flow cell, SMRT Cell, or kit configuration.",
            )

        flow_cell_platforms = _filter_platforms(
            instrument_platforms, flow_cell=selected_flow_cell
        )

        with col_read_length:
            read_length_options = _ordered_unique(
                _platform_field(platform, "read_length")
                for platform in flow_cell_platforms.values()
            )
            selected_read_length = st.selectbox(
                "Read length",
                options=read_length_options,
                index=_select_index(
                    read_length_options,
                    _platform_field(default_platform, "read_length"),
                ),
                help="Only read lengths valid for the selected flow cell / kit are shown.",
            )

        matching_platforms = _filter_platforms(
            flow_cell_platforms, read_length=selected_read_length
        )
        if not matching_platforms:
            st.error("No platform configuration matches the selected options.")
            st.stop()

        if len(matching_platforms) == 1:
            platform_id, platform = next(iter(matching_platforms.items()))
        else:
            matching_ids = list(matching_platforms.keys())
            matching_names = [matching_platforms[pid]["name"] for pid in matching_ids]
            selected_name = st.selectbox(
                "Configuration",
                options=matching_names,
                index=0,
                help="Multiple platform definitions matched; choose the exact configuration.",
            )
            platform_id = matching_ids[matching_names.index(selected_name)]
            platform = PLATFORM_CONFIG[platform_id]

        st.caption(f"Selected configuration: {platform['name']}.")
        output_bp, runtime_hr = _platform_output_ui(platform, runtime_hr)

    return platform_id, platform, output_bp, runtime_hr


def region_size_input_ui(
    coverage_mode: str,
    variable: str,
    preset_values,
    params,
    region_input: str,
    *,
    compact: bool = False,
) -> Tuple[int, str, int, int]:
    """
    Handles region/amplicon input widgets.
    Returns: region_size, region_input, num_amplicons, amplicon_size
    """
    num_amplicons = params.get("num_amplicons", 0)
    amplicon_size = params.get("amplicon_size", 0)

    with st.container(border=True):
        if coverage_mode == "Targeted Panel":
            if preset_values is not None:
                default_num_amplicons = preset_values.amplicon_count or 1
                default_amplicon_size = round(
                    preset_values.region_bp / default_num_amplicons
                )
            else:
                default_num_amplicons = num_amplicons
                default_amplicon_size = amplicon_size

            def num_amplicons_input() -> int:
                return int(
                    st.number_input(
                        "Number of Amplicons",
                        min_value=1,
                        value=default_num_amplicons,
                        step=10,
                        key="num_amplicons_input",
                        help="Total number of unique amplicons in your panel.",
                    )
                )

            def amplicon_size_input() -> int:
                return int(
                    st.number_input(
                        "Avg Amplicon Size (bp)",
                        min_value=50,
                        value=default_amplicon_size,
                        step=25,
                        key="amplicon_size_input",
                        help="Average size (in bp) of each amplicon.",
                    )
                )

            if compact:
                num_amplicons = num_amplicons_input()
                amplicon_size = amplicon_size_input()
            else:
                col_n_amp, col_amp_size = st.columns(2)
                with col_n_amp:
                    num_amplicons = num_amplicons_input()
                with col_amp_size:
                    amplicon_size = amplicon_size_input()

            region_size = num_amplicons * amplicon_size
            region_input = f"{region_size} bp"
            st.caption(f"Total region size: {format_region_size(region_size)}")
        else:
            region_input = st.text_input(
                "Genome/Region Size",
                value=region_input,
                disabled=variable == "Genome size",
                help="Total size of region to cover (e.g. '3.3 Gb', '50 Mb', '1200000').",
            )
            try:
                region_size = parse_region_size(region_input) if region_input else 1
            except Exception:
                st.warning(
                    "Could not parse region size. Enter a value like '3.3 Gb' or '5000000'."
                )
                region_size = 1

    return region_size, region_input, num_amplicons, amplicon_size


def amplicon_planning_controls_ui(
    preset_values,
    params,
    *,
    bordered: bool = True,
    compact: bool = False,
    disabled: bool = False,
    disable_min_reads: bool = False,
) -> Tuple[int, float]:
    """
    Controls for amplicon read-count planning.

    Use ``compact=True`` when the controls are placed in a narrow column, such
    as the former mean-depth input card. Use ``disable_min_reads=True`` when the
    calculator is solving for achieved amplicon depth rather than using a
    requested minimum read-count target. The imbalance factor remains active in
    that mode because it directly affects the estimated minimum read count.

    Returns:
      (minimum reads/read-pairs per amplicon, imbalance factor)
    """
    default_min_reads = int(
        getattr(preset_values, "min_reads_per_amplicon", None)
        or params.get("min_reads_per_amplicon", 500)
    )
    default_imbalance = float(
        getattr(preset_values, "amplicon_imbalance_factor", None)
        or params.get("amplicon_imbalance_factor", 3.0)
    )

    container_context = st.container(border=bordered) if bordered else nullcontext()

    with container_context:
        if compact:
            st.markdown("**Depth / amplicon**")
        else:
            st.subheader("Amplicon read planning", anchor=False)

        def min_reads_input() -> int:
            return int(
                st.number_input(
                    (
                        "Min reads / amplicon"
                        if compact
                        else "Minimum reads/read-pairs per amplicon"
                    ),
                    min_value=1,
                    value=max(1, default_min_reads),
                    step=100,
                    help=(
                        "Desired usable non-duplicate, on-target read units for each amplicon. "
                        "For paired-end Illumina runs, one unit is one read pair."
                    ),
                    disabled=disabled or disable_min_reads,
                )
            )

        def imbalance_input() -> float:
            return float(
                st.number_input(
                    "Imbalance factor" if compact else "Amplicon imbalance factor",
                    min_value=1.0,
                    max_value=100.0,
                    value=max(1.0, default_imbalance),
                    step=0.5,
                    help=(
                        "Multiplier for primer/pool imbalance. A value of 3 means the panel is "
                        "planned so the lower-coverage amplicons still receive roughly the "
                        "minimum requested reads."
                    ),
                    disabled=disabled,
                )
            )

        if compact:
            min_reads_per_amplicon = min_reads_input()
            amplicon_imbalance_factor = imbalance_input()
        else:
            col_min_reads, col_imbalance = st.columns(2)
            with col_min_reads:
                min_reads_per_amplicon = min_reads_input()
            with col_imbalance:
                amplicon_imbalance_factor = imbalance_input()

        if disabled:
            st.caption(
                "Disabled because this field is not used for the current solve mode."
            )
        elif disable_min_reads:
            st.caption(
                "Min reads is disabled while solving for achieved amplicon depth. "
                "Imbalance remains active."
                if compact
                else (
                    "Minimum reads/read-pairs is disabled because Depth is being solved. "
                    "Amplicon imbalance remains active because it changes the estimated "
                    "minimum reads/read-pairs per amplicon."
                )
            )
        else:
            st.caption(
                "Uses read units per amplicon, not whole-panel base coverage."
                if compact
                else (
                    "Targeted amplicon calculations use read units per amplicon rather than "
                    "average base coverage across the whole panel."
                )
            )

    return int(min_reads_per_amplicon), float(amplicon_imbalance_factor)


def shotgun_metagenomics_input_ui(preset_values, params) -> float:
    """Control for shotgun metagenomics data-volume planning."""
    default_gb = float(
        getattr(preset_values, "gb_per_sample", None)
        or params.get("shotgun_gb_per_sample", 5.0)
    )
    with st.container(border=True):
        st.subheader("Shotgun metagenomics target", anchor=False)
        gb_per_sample = st.number_input(
            "Usable data per sample (Gb)",
            min_value=0.01,
            value=max(0.01, default_gb),
            step=0.5,
            help=(
                "Shotgun metagenomics is planned by data volume per sample, not by "
                "coverage of a single marker amplicon."
            ),
        )
        st.caption(
            "This target is interpreted after read filtering, duplication, and on-target "
            "or usable-data filters."
        )
    return float(gb_per_sample)


def show_amplicon_plan_ui(
    plan: AmpliconPlan,
    *,
    min_reads_per_amplicon: int,
    amplicon_imbalance_factor: float,
) -> None:
    """Display read-pair/read-unit planning metrics for amplicon panels."""
    with st.container(border=True):
        st.subheader("Amplicon read-count summary", anchor=False)
        col_sample, col_mean, col_adjusted, col_dropout = st.columns(4)
        unit = plan.read_unit_label
        with col_sample:
            st.metric(
                f"Usable {unit}/sample",
                f"{plan.usable_read_units_per_sample:,.0f}",
                delta_color="off",
            )
        with col_mean:
            st.metric(
                f"Mean {unit}/amplicon",
                f"{plan.mean_read_units_per_amplicon:,.0f}",
                delta_color="off",
            )
        with col_adjusted:
            st.metric(
                "Imbalance-adjusted minimum",
                f"{plan.imbalance_adjusted_read_units_per_amplicon:,.0f}",
                delta=f"target ≥ {min_reads_per_amplicon:,}",
                delta_color="off",
            )
        with col_dropout:
            st.metric(
                "Estimated below-target/dropout amplicons",
                f"{plan.estimated_below_target_amplicons:,.1f}",
                delta_color="off",
            )
        st.caption(
            f"Read-unit conversion used {plan.bases_per_unit:,} bp per {unit[:-1] if unit.endswith('s') else unit}; "
            f"imbalance factor = {amplicon_imbalance_factor:.2f}. "
            "The dropout estimate is a planning heuristic based on the shortfall between "
            "the imbalance-adjusted read count and the requested minimum."
        )


def show_shotgun_plan_ui(
    *, usable_gb_per_sample: float, target_gb_per_sample: float
) -> None:
    """Display shotgun metagenomics data-volume planning metrics."""
    with st.container(border=True):
        st.subheader("Shotgun metagenomics summary", anchor=False)
        col_usable, col_target = st.columns(2)
        with col_usable:
            st.metric(
                "Usable Gb/sample",
                f"{usable_gb_per_sample:.2f}",
                delta_color="off",
            )
        with col_target:
            st.metric(
                "Target Gb/sample",
                f"{target_gb_per_sample:.2f}",
                delta_color="off",
            )
        st.caption(
            "This mode uses data volume per sample instead of target-region coverage."
        )


# ----------------------------
# ddRAD configuration controls
# ----------------------------
def ddrad_config_ui(
    *, preset_values, params, show_panel: bool
) -> Tuple[bool, float, str, int, int]:
    """
    ddRAD is always configured from a known whole-genome size and a target
    fraction. The selected target region is then used for all solve modes.

    Returns:
      (enabled, target_fraction_pct, known_genome_input, known_genome_bp, target_region_bp)
    """
    if not show_panel:
        return (
            False,
            float(params.get("target_fraction_pct", 2.0)),
            params.get("known_genome_input", "3.3 Gb"),
            0,
            0,
        )

    enabled = bool(
        preset_values is not None
        and getattr(preset_values, "target_fraction_pct", None) is not None
    )
    default_fraction = (
        float(preset_values.target_fraction_pct)
        if enabled and preset_values.target_fraction_pct is not None
        else float(params.get("target_fraction_pct", 2.0))
    )

    with st.container(border=True):
        st.subheader("Reduced representation (ddRAD) options", anchor=False)
        known_genome_input = st.text_input(
            "Known whole-genome size",
            value=params.get("known_genome_input", "3.3 Gb"),
            help="Example: '3.3 Gb' (human) or '5 Mb' (bacteria).",
        )
        target_fraction_default = max(
            0.01, min(100.0, float(params.get("target_fraction_pct", default_fraction)))
        )
        target_fraction_pct = st.number_input(
            "Target fraction of genome (%)",
            min_value=0.01,
            max_value=100.0,
            value=target_fraction_default,
            step=0.01,
            format="%.2f",
            help=(
                "Fraction of the known genome represented by the ddRAD library. "
                "The calculator uses known genome size × this fraction as the target region."
            ),
        )

        try:
            known_genome_bp = parse_region_size(known_genome_input)
        except Exception:
            st.warning(
                "Could not parse known genome size. Enter a value like '3.3 Gb' or '5 Mb'."
            )
            known_genome_bp = 1

        target_region_bp = max(
            1, int(known_genome_bp * (float(target_fraction_pct) / 100.0))
        )
        st.caption(
            "ddRAD target region: "
            f"{format_region_size(target_region_bp)} "
            f"({target_fraction_pct:.2f}% of {format_region_size(known_genome_bp)})."
        )

    return (
        True,
        float(target_fraction_pct),
        known_genome_input,
        int(known_genome_bp),
        int(target_region_bp),
    )
