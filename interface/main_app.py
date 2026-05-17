# interface/main_app.py

from __future__ import annotations

import streamlit as st

from coverage_calculator.calculator.amplicon_model import (
    calc_amplicon_plan,
    calc_amplicon_samples_per_flow_cell,
    calc_amplicon_supported_region_bp,
)
from coverage_calculator.calculator.coverage_model import CoverageCalculator
from coverage_calculator.calculator.effective_output import (
    compute_effective_output,
    EffectiveOutputStages,
)
from coverage_calculator.config.platforms import PLATFORM_CONFIG
from coverage_calculator.config.presets import (
    GENOME_WIDE_PRESETS,
    TARGETED_PRESETS,
)
from coverage_calculator.utils.query_state import (
    load_query_params,
    update_query_params,
)
from coverage_calculator.utils.unit_parser import format_region_size
from interface.ui_helpers import (
    advanced_options_ui,
    amplicon_planning_controls_ui,
    ddrad_config_ui,
    dedup_on_target_ui,
    platform_selector_ui,
    preset_select_ui,
    region_size_input_ui,
    run_planning_ui,
    run_unit_labels,
    shotgun_metagenomics_input_ui,
    show_amplicon_plan_ui,
    show_results_rail_ui,
    show_shotgun_plan_ui,
)
from interface.math_explainer import (
    render_amplicon_math_explainer,
    render_math_explainer,
    render_run_planning_math_explainer,
    render_shotgun_math_explainer,
)

RUN_PLANNING_VARIABLE = "Flow cells / runs required"
VARIABLE_OPTIONS = [
    "Samples per flow cell",
    "Depth",
    "Genome size",
    RUN_PLANNING_VARIABLE,
]
VARIABLE_ALIASES = {
    "Flow cells required": RUN_PLANNING_VARIABLE,
    "Operational run planning": RUN_PLANNING_VARIABLE,
    "Run planning": RUN_PLANNING_VARIABLE,
}
VARIABLE_DISPLAY_LABELS = {
    "Samples per flow cell": "Samples / flow cell",
    "Depth": "Depth",
    "Genome size": "Genome size",
    RUN_PLANNING_VARIABLE: "Runs required",
}


def _format_count(value: float) -> str:
    """Compact count formatting for the right-side result rail."""

    abs_value = abs(float(value))
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f} M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f} K"
    return f"{value:.0f}"


def _inject_layout_css() -> None:
    """Small, theme-aware layout polish for the results-first view."""

    st.markdown(
        """
<style>
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] > .main .block-container {
    /* Leave room for Streamlit's top toolbar and browser chrome so the custom
       header is not clipped at the top of the viewport. */
    padding-top: clamp(2.6rem, 4vh, 3.4rem);
    padding-bottom: 2.8rem;
}

.seqcalc-title {
    margin: 0 0 0.16rem 0;
    padding-top: 0.08rem;
    font-size: clamp(2.15rem, 3.5vw, 3rem);
    line-height: 1.14;
    font-weight: 780;
    letter-spacing: -0.045em;
    color: var(--text-color);
    overflow: visible;
}

.seqcalc-subtitle {
    margin: 0 0 0.95rem 0;
    color: var(--secondary-text-color);
    font-size: 0.98rem;
}

.seqcalc-step-header {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    margin: 0 0 0.9rem 0;
}

.seqcalc-step-badge {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.15rem;
    height: 2.15rem;
    border-radius: 999px;
    color: #ffffff;
    font-weight: 800;
    font-size: 1rem;
    background: #2f80ff;
    box-shadow: 0 0 0 1px rgba(122, 171, 255, 0.45);
}

.seqcalc-step-title {
    color: var(--text-color);
    font-weight: 760;
    font-size: 1.05rem;
    line-height: 1.15;
}

.seqcalc-step-desc {
    color: var(--secondary-text-color);
    font-size: 0.78rem;
    line-height: 1.25;
    margin-top: 0.12rem;
}

.seqcalc-result-hero {
    text-align: center;
    padding: clamp(2.7rem, 7vh, 4.4rem) 0.75rem 1.7rem 0.75rem;
}

.seqcalc-result-label {
    color: var(--secondary-text-color);
    font-size: clamp(1.02rem, 1.25vw, 1.24rem);
    font-weight: 600;
    margin-bottom: 0.8rem;
}

.seqcalc-result-value {
    color: #2f80ff;
    font-size: clamp(3rem, 5.4vw, 4.8rem);
    line-height: 0.98;
    font-weight: 820;
    letter-spacing: -0.06em;
}

.seqcalc-result-delta {
    color: var(--secondary-text-color);
    font-size: clamp(0.9rem, 1.05vw, 1.05rem);
    margin-top: 0.85rem;
}

.seqcalc-summary-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.18rem 0;
}

.seqcalc-summary-label {
    color: var(--secondary-text-color);
    font-size: 0.84rem;
}

.seqcalc-summary-value {
    color: var(--text-color);
    font-size: 0.88rem;
    font-weight: 650;
    text-align: right;
}

.seqcalc-metric-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    column-gap: 1rem;
    align-items: baseline;
    padding: 0.48rem 0;
}

.seqcalc-metric-label {
    color: var(--text-color);
    font-weight: 650;
}

.seqcalc-metric-value {
    color: var(--text-color);
    font-weight: 650;
    text-align: right;
    white-space: nowrap;
}

div[role="radiogroup"] > label {
    margin-bottom: 0.18rem;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: color-mix(in srgb, var(--secondary-background-color) 74%, transparent);
}

[data-testid="stExpander"] {
    background: color-mix(in srgb, var(--secondary-background-color) 78%, transparent);
}

@media (max-width: 980px) {
    .seqcalc-result-hero { padding-top: 2rem; }
    .seqcalc-step-header { align-items: flex-start; }
}
</style>
""",
        unsafe_allow_html=True,
    )


def _render_compact_header() -> None:
    st.markdown(
        """
<div class="seqcalc-title">Sequencing Coverage Calculator</div>
<div class="seqcalc-subtitle">Follow the steps on the left to configure your assay. Results update automatically.</div>
""",
        unsafe_allow_html=True,
    )


def _render_step_header(step: int, title: str, description: str) -> None:
    """Render a lightweight numbered section header."""

    st.markdown(
        f"""
<div class="seqcalc-step-header">
  <div class="seqcalc-step-badge">{step}</div>
  <div>
    <div class="seqcalc-step-title">{title}</div>
    <div class="seqcalc-step-desc">{description}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _run_summary_rows(
    *,
    coverage_mode: str,
    preset_label: str,
    platform_name: str,
    runtime_hr: int | float | None = None,
    runtime_scaled: bool = False,
) -> list[tuple[str, str]]:
    rows = [
        ("Mode", coverage_mode),
        ("Preset", preset_label or "Custom"),
        ("Platform", platform_name),
    ]
    if runtime_scaled and runtime_hr is not None:
        rows.append(("Runtime", f"{float(runtime_hr):.0f} hours"))
    return rows


def _variable_selector_ui(default_variable: str) -> str:
    """Render the solve-for control as a compact horizontal selector."""

    help_text = (
        "Pick which variable you'd like to solve for. In amplicon mode, "
        "'Depth' reports imbalance-adjusted reads/read-pairs per amplicon. "
        f"'{RUN_PLANNING_VARIABLE}' calculates the integer number of flow cells, "
        "SMRT Cells, or runs required from your sample count and per-sample targets."
    )

    if hasattr(st, "segmented_control"):
        try:
            selected = st.segmented_control(
                "Variable to calculate:",
                VARIABLE_OPTIONS,
                selection_mode="single",
                default=default_variable,
                required=True,
                format_func=lambda option: VARIABLE_DISPLAY_LABELS.get(option, option),
                help=help_text,
                key="variable_to_calculate_segmented",
                width="stretch",
            )
        except TypeError:
            # Older Streamlit versions may expose st.segmented_control without
            # the newer required/width arguments. Keep the UI usable if the
            # dependency is not pinned tightly.
            selected = st.segmented_control(
                "Variable to calculate:",
                VARIABLE_OPTIONS,
                selection_mode="single",
                default=default_variable,
                format_func=lambda option: VARIABLE_DISPLAY_LABELS.get(option, option),
                help=help_text,
                key="variable_to_calculate_segmented",
            )
        return str(selected or default_variable)

    # Fallback for older Streamlit releases that do not have segmented controls.
    return st.radio(
        "Variable to calculate:",
        VARIABLE_OPTIONS,
        horizontal=True,
        help=help_text,
        index=VARIABLE_OPTIONS.index(default_variable),
    )


def run() -> None:
    params = load_query_params()
    _inject_layout_css()
    _render_compact_header()

    # Load initial state from query or use defaults.
    region_input = params.get("region_input", "3.3 Gb")
    num_amplicons = params.get("num_amplicons", 0)
    amplicon_size = params.get("amplicon_size", 0)
    min_reads_per_amplicon = params.get("min_reads_per_amplicon", 500)
    amplicon_imbalance_factor = params.get("amplicon_imbalance_factor", 3.0)
    shotgun_gb_per_sample = params.get("shotgun_gb_per_sample", 5.0)

    controls_col, results_col = st.columns([3.05, 2], gap="large")

    with results_col:
        # Filled after the calculation finishes, but reserved here so the
        # right-hand rail owns the output area from the top of the page.
        result_placeholder = st.empty()
        warning_placeholder = st.empty()

    with controls_col:
        with st.container(border=True):
            _render_step_header(
                1,
                "Assay setup",
                "Choose the overall sequencing mode and optionally start from a protocol preset.",
            )
            setup_mode_col, setup_preset_col = st.columns([1, 1.15], gap="small")
            with setup_mode_col:
                with st.container(border=True):
                    coverage_mode = st.radio(
                        "Coverage Mode",
                        ["Genome-wide", "Targeted Panel"],
                        help=(
                            "Choose 'Genome-wide' for whole-genome, exome, ddRAD, or shotgun "
                            "metagenomics planning. Use 'Targeted Panel' for targeted amplicon "
                            "or marker-amplicon assays."
                        ),
                        index=["Genome-wide", "Targeted Panel"].index(
                            params["coverage_mode"]
                        ),
                    )

            with setup_preset_col:
                with st.container(border=True):
                    preset_label, preset_values, _active_presets = preset_select_ui(
                        coverage_mode, params, GENOME_WIDE_PRESETS, TARGETED_PRESETS
                    )

        default_variable = VARIABLE_ALIASES.get(params["variable"], params["variable"])
        if default_variable not in VARIABLE_OPTIONS:
            default_variable = "Samples per flow cell"

        with st.container(border=True):
            _render_step_header(
                2,
                "Solve for",
                "Select the value the calculator should estimate from the constraints below.",
            )
            variable = _variable_selector_ui(default_variable)

        is_ddrad_preset = (
            coverage_mode == "Genome-wide"
            and preset_values is not None
            and getattr(preset_values, "target_fraction_pct", None) is not None
        )
        is_shotgun_metagenomics = (
            coverage_mode == "Genome-wide"
            and preset_values is not None
            and getattr(preset_values, "gb_per_sample", None) is not None
        )
        is_amplicon_mode = coverage_mode == "Targeted Panel"
        is_run_planning_variable = variable == RUN_PLANNING_VARIABLE

        if preset_values is not None:
            if is_amplicon_mode:
                num_amplicons = preset_values.amplicon_count or 1
                amplicon_size = round(preset_values.region_bp / num_amplicons)
                region_input = f"{num_amplicons * amplicon_size} bp"
                min_reads_per_amplicon = (
                    preset_values.min_reads_per_amplicon or min_reads_per_amplicon
                )
                amplicon_imbalance_factor = (
                    preset_values.amplicon_imbalance_factor or amplicon_imbalance_factor
                )
            elif is_shotgun_metagenomics:
                shotgun_gb_per_sample = (
                    preset_values.gb_per_sample or shotgun_gb_per_sample
                )
                region_input = f"{shotgun_gb_per_sample:g} Gb/sample"
            elif not is_ddrad_preset:
                region_input = format_region_size(preset_values.region_bp)

        # Defaults for modes that do not display ddRAD controls.
        ddrad_enabled = False
        target_fraction_pct = float(params.get("target_fraction_pct", 2.0))
        known_genome_input = params.get("known_genome_input", "3.3 Gb")
        known_genome_bp_val = None
        run_planning_placeholder = None

        with st.container(border=True):
            _render_step_header(
                3,
                "Target values",
                "Enter the assay region, depth or read target, and sample constraints.",
            )
            col_size, col_depth, col_samples = st.columns(
                [1.04, 1.06, 0.9], gap="small"
            )

            with col_size:
                if is_ddrad_preset:
                    (
                        ddrad_enabled,
                        target_fraction_pct,
                        known_genome_input,
                        known_genome_bp,
                        ddrad_target_region_bp,
                    ) = ddrad_config_ui(
                        preset_values=preset_values,
                        params=params,
                        show_panel=True,
                    )
                    known_genome_bp_val = known_genome_bp
                    region_size = ddrad_target_region_bp
                    region_input = format_region_size(region_size)
                    st.caption(
                        "This computed ddRAD target region is used for samples-per-flow-cell, "
                        "depth, and supported-genome calculations."
                    )
                elif is_shotgun_metagenomics:
                    shotgun_gb_per_sample = shotgun_metagenomics_input_ui(
                        preset_values, params
                    )
                    # Keep a positive placeholder region for advanced-output models that
                    # require one, but do not use it for shotgun metagenomics calculations.
                    region_size = 1
                    region_input = f"{shotgun_gb_per_sample:g} Gb/sample"
                else:
                    region_size, region_input, num_amplicons, amplicon_size = (
                        region_size_input_ui(
                            coverage_mode,
                            variable,
                            preset_values,
                            params,
                            region_input,
                            compact=True,
                        )
                    )

            depth = params["depth"]
            with col_depth:
                with st.container(border=True):
                    if is_amplicon_mode:
                        min_reads_per_amplicon, amplicon_imbalance_factor = (
                            amplicon_planning_controls_ui(
                                preset_values,
                                params,
                                bordered=False,
                                compact=True,
                                disable_min_reads=variable == "Depth",
                            )
                        )
                    else:
                        depth_disabled = variable == "Depth" or is_shotgun_metagenomics
                        depth = st.number_input(
                            "Mean target depth (X)",
                            value=params["depth"],
                            disabled=depth_disabled,
                            step=5,
                            min_value=1,
                            help=(
                                "For shotgun metagenomics presets, planning is based on "
                                "Gb-per-sample targets instead of this mean-depth field."
                            ),
                        )
                        if is_shotgun_metagenomics:
                            st.info(
                                "Shotgun metagenomics mode uses usable Gb per sample, not depth."
                            )
                        elif coverage_mode == "Genome-wide" and depth < 20:
                            st.info(
                                "Whole genome sequencing usually aims for at least 20X."
                            )

            with col_samples:
                with st.container(border=True):
                    samples = st.number_input(
                        "Samples",
                        value=params["samples"],
                        step=1,
                        disabled=variable == "Samples per flow cell",
                        min_value=1,
                    )

            if is_run_planning_variable:
                run_planning_placeholder = st.empty()

        with st.container(border=True):
            _render_step_header(
                4,
                "Sequencing output",
                "Select the sequencing platform and run configuration.",
            )
            platform_id, platform, output_bp, runtime_hr = platform_selector_ui(
                params, PLATFORM_CONFIG, cascade=True, bordered=False
            )

        with st.container(border=True):
            _render_step_header(
                5,
                "QC & yield modifiers",
                "Account for losses, enrichment specificity, and optional modeling assumptions.",
            )
            duplication, on_target = dedup_on_target_ui(
                preset_values,
                params,
                bordered=True,
                show_preset_values=True,
            )

            (
                apply_gc_bias,
                gc_bias_percent,
                apply_fragment_model,
                fragment_size,
                read_length,
                read_filter_loss,
            ) = advanced_options_ui(
                "Targeted Panel" if is_shotgun_metagenomics else coverage_mode,
                params,
                platform_id,
                platform,
            )

    # --- Effective output stages (single source of truth) ---
    safe_region_for_model = max(1, int(region_size))
    stages: EffectiveOutputStages = compute_effective_output(
        base_output_bp=float(output_bp),
        read_filter_loss_pct=float(read_filter_loss),
        apply_fragment_model=apply_fragment_model,
        fragment_size=fragment_size,
        read_length=read_length,
        apply_gc_bias=apply_gc_bias,
        gc_bias_pct=float(gc_bias_percent),
        duplication_pct=float(duplication),
        on_target_pct=float(on_target),
    )
    total_bp = stages.o4  # Effective output after all stages

    amplicon_plan = None
    shotgun_usable_gb_per_sample = 0.0
    capacity_samples_per_unit = 0.0
    planning_samples = int(params.get("planning_samples", max(1, int(samples))))
    reserve_margin_pct = float(params.get("reserve_margin_pct", 15.0))

    # --- Prepare result metric ---
    if is_amplicon_mode:
        amplicon_plan = calc_amplicon_plan(
            output_bp=total_bp,
            samples=int(samples),
            eff_fraction=stages.eff_fraction,
            num_amplicons=int(num_amplicons),
            amplicon_size_bp=int(amplicon_size),
            min_reads_per_amplicon=int(min_reads_per_amplicon),
            imbalance_factor=float(amplicon_imbalance_factor),
            platform=platform,
        )

        capacity_samples_per_unit = calc_amplicon_samples_per_flow_cell(
            output_bp=total_bp,
            eff_fraction=stages.eff_fraction,
            num_amplicons=int(num_amplicons),
            min_reads_per_amplicon=int(min_reads_per_amplicon),
            imbalance_factor=float(amplicon_imbalance_factor),
            bases_per_read_unit=amplicon_plan.bases_per_unit,
        )

        if variable == "Samples per flow cell":
            result = capacity_samples_per_unit
            label = "Samples per Flow Cell"
            value = f"{result:.1f}"
            delta = (
                f"at ≥{min_reads_per_amplicon:,} usable "
                f"{amplicon_plan.read_unit_label}/amplicon across "
                f"{num_amplicons:,} amplicons"
            )
        elif variable == "Depth":
            result = amplicon_plan.imbalance_adjusted_read_units_per_amplicon
            label = f"Estimated Minimum {amplicon_plan.read_unit_label.title()} per Amplicon"
            value = f"{result:,.0f}"
            delta = (
                f"mean {amplicon_plan.mean_read_units_per_amplicon:,.0f} "
                f"{amplicon_plan.read_unit_label}/amplicon before imbalance"
            )
        elif variable == "Genome size":
            result = calc_amplicon_supported_region_bp(
                output_bp=total_bp,
                samples=int(samples),
                eff_fraction=stages.eff_fraction,
                amplicon_size_bp=int(amplicon_size),
                min_reads_per_amplicon=int(min_reads_per_amplicon),
                imbalance_factor=float(amplicon_imbalance_factor),
                bases_per_read_unit=amplicon_plan.bases_per_unit,
            )
            supported_amplicons = result / max(1, int(amplicon_size))
            label = "Supported Amplicon Panel Size"
            value = format_region_size(int(result))
            delta = (
                f"≈{supported_amplicons:,.0f} amplicons at "
                f"≥{min_reads_per_amplicon:,} usable "
                f"{amplicon_plan.read_unit_label}/amplicon"
            )

    elif is_shotgun_metagenomics:
        usable_total_bp = total_bp * stages.eff_fraction
        shotgun_usable_gb_per_sample = (usable_total_bp / max(1, int(samples))) / 1e9
        target_bp_per_sample = max(0.01, float(shotgun_gb_per_sample)) * 1e9

        capacity_samples_per_unit = (
            usable_total_bp / target_bp_per_sample if target_bp_per_sample else 0.0
        )

        if variable == "Samples per flow cell":
            result = capacity_samples_per_unit
            label = "Samples per Flow Cell"
            value = f"{result:.1f}"
            delta = f"at {shotgun_gb_per_sample:.2f} usable Gb/sample"
        elif variable == "Depth":
            result = shotgun_usable_gb_per_sample
            label = "Usable Data per Sample"
            value = f"{result:.2f} Gb"
            delta = f"across {samples} samples using {platform['name']}"
        elif variable == "Genome size":
            result = shotgun_usable_gb_per_sample
            label = "Usable Data per Sample"
            value = f"{result:.2f} Gb"
            delta = "Genome-size solving is not meaningful for shotgun metagenomics"

    else:
        # --- Calculator using the effective output + eff fraction ---
        calc = CoverageCalculator(
            region_size_bp=safe_region_for_model,
            depth=depth,
            samples=samples,
            output_bp=total_bp,
            duplication_pct=duplication,
            on_target_pct=on_target,
        )

        capacity_samples_per_unit = calc.calc_samples_per_flow_cell()

        if variable == "Samples per flow cell":
            result = capacity_samples_per_unit
            label = "Samples per Flow Cell"
            value = f"{result:.1f}"
            delta = f"at {depth:.1f}X genome-wide"

        elif variable == "Depth":
            result = calc.calc_depth()
            label = "Estimated Depth"
            value = f"{result:.1f}X"
            delta = f"Genome-wide across {samples} samples using {platform['name']}"

        elif variable == "Genome size":
            target_region_bp = calc.calc_genome_size()  # G_target at depth D across S
            if ddrad_enabled:
                f = max(0.0001, float(target_fraction_pct) / 100.0)
                result = target_region_bp / f
                label = "Supported Whole-Genome Size (ddRAD)"
                value = format_region_size(int(result))
                delta = (
                    f"from target fraction {target_fraction_pct:.2f}% at {depth:.1f}X "
                    f"across {samples} samples"
                )
            else:
                result = target_region_bp
                label = "Supported Region Size"
                value = format_region_size(int(result))
                delta = f"at {depth:.1f}X depth for {samples} samples"

    run_plan = None
    if is_run_planning_variable:
        if run_planning_placeholder is None:
            run_plan, planning_samples, reserve_margin_pct = run_planning_ui(
                params=params,
                samples_per_unit=capacity_samples_per_unit,
                default_samples_to_plan=int(samples),
                platform=platform,
                show_sample_input=False,
                planning_samples_override=int(samples),
                compact=True,
            )
        else:
            with run_planning_placeholder.container():
                run_plan, planning_samples, reserve_margin_pct = run_planning_ui(
                    params=params,
                    samples_per_unit=capacity_samples_per_unit,
                    default_samples_to_plan=int(samples),
                    platform=platform,
                    show_sample_input=False,
                    planning_samples_override=int(samples),
                    compact=True,
                )
        singular_unit, plural_unit = run_unit_labels(platform)
        result = run_plan.units_required
        label_unit = (
            plural_unit if plural_unit.startswith("SMRT") else plural_unit.capitalize()
        )
        label = f"{label_unit} Required"
        value = "—" if run_plan.units_required <= 0 else f"{run_plan.units_required:d}"
        delta = (
            f"{planning_samples:,} samples at {reserve_margin_pct:.0f}% reserve; "
            f"{capacity_samples_per_unit:.1f} theoretical samples/{singular_unit}"
        )

    supporting_metrics = [
        ("Effective output", format_region_size(int(total_bp))),
        ("Usable fraction", f"{stages.eff_fraction * 100:.1f}%"),
        ("Platform", platform["name"]),
    ]
    if run_plan is not None:
        singular_unit, _plural_unit = run_unit_labels(platform)
        supporting_metrics = [
            (
                f"Theoretical samples/{singular_unit}",
                f"{capacity_samples_per_unit:.1f}",
            ),
            ("Reserve margin", f"{reserve_margin_pct:.0f}%"),
            ("Samples to plan", f"{planning_samples:,}"),
        ]
    elif amplicon_plan is not None:
        supporting_metrics = [
            (
                f"Usable {amplicon_plan.read_unit_label}/sample",
                _format_count(amplicon_plan.usable_read_units_per_sample),
            ),
            (
                f"Mean {amplicon_plan.read_unit_label}/amplicon",
                _format_count(amplicon_plan.mean_read_units_per_amplicon),
            ),
            (
                "Total panel region",
                format_region_size(int(num_amplicons * amplicon_size)),
            ),
        ]
    elif is_shotgun_metagenomics:
        supporting_metrics = [
            ("Usable Gb/sample", f"{shotgun_usable_gb_per_sample:.2f}"),
            ("Target Gb/sample", f"{shotgun_gb_per_sample:.2f}"),
            ("Effective output", format_region_size(int(total_bp))),
        ]

    show_results_rail_ui(
        result_placeholder,
        warning_placeholder,
        variable,
        result,
        label,
        value,
        delta,
        total_bp,
        num_amplicons=num_amplicons if is_amplicon_mode else None,
        supporting_metrics=supporting_metrics,
        summary_rows=_run_summary_rows(
            coverage_mode=coverage_mode,
            preset_label=preset_label,
            platform_name=platform["name"],
            runtime_hr=runtime_hr,
            runtime_scaled=bool(platform.get("bp_per_minute")),
        ),
    )

    # “How the math works” explainer stays in the left/calculator lane.
    math_variable = "Samples per flow cell" if is_run_planning_variable else variable
    math_result_value = (
        capacity_samples_per_unit if is_run_planning_variable else result
    )

    with results_col:
        if amplicon_plan is not None:
            render_amplicon_math_explainer(
                variable=math_variable,
                plan=amplicon_plan,
                num_amplicons=int(num_amplicons),
                amplicon_size_bp=int(amplicon_size),
                min_reads_per_amplicon=int(min_reads_per_amplicon),
                amplicon_imbalance_factor=float(amplicon_imbalance_factor),
                samples=int(samples),
                output_bp=float(total_bp),
                eff_fraction=float(stages.eff_fraction),
                result_value=(
                    float(math_result_value)
                    if isinstance(math_result_value, (int, float))
                    else 0.0
                ),
            )
        elif is_shotgun_metagenomics:
            render_shotgun_math_explainer(
                variable=math_variable,
                target_gb_per_sample=float(shotgun_gb_per_sample),
                usable_gb_per_sample=float(shotgun_usable_gb_per_sample),
                samples=int(samples),
                output_bp=float(total_bp),
                eff_fraction=float(stages.eff_fraction),
                result_value=(
                    float(math_result_value)
                    if isinstance(math_result_value, (int, float))
                    else 0.0
                ),
            )
        else:
            render_math_explainer(
                variable=math_variable,
                region_size_bp=safe_region_for_model,
                depth=float(depth),
                samples=int(samples),
                platform_name=platform["name"],
                stages=stages,
                duplication_pct=float(duplication),
                on_target_pct=float(on_target),
                read_filter_loss=float(read_filter_loss),
                apply_fragment_model=apply_fragment_model,
                fragment_size=fragment_size,
                read_length=read_length,
                applied_gc_bias=apply_gc_bias,
                gc_bias_percent=float(gc_bias_percent),
                result_value=(
                    float(math_result_value)
                    if isinstance(math_result_value, (int, float))
                    else 0.0
                ),
                ddrad_enabled=ddrad_enabled,
                ddrad_mode="fraction_to_genome",
                target_fraction_pct=float(target_fraction_pct),
                known_genome_bp=known_genome_bp_val,
            )

        if run_plan is not None:
            singular_unit, plural_unit = run_unit_labels(platform)
            render_run_planning_math_explainer(
                plan=run_plan,
                singular_unit=singular_unit,
                plural_unit=plural_unit,
            )

    # Detailed summaries remain below the main two-column workspace.
    if amplicon_plan is not None:
        show_amplicon_plan_ui(
            amplicon_plan,
            min_reads_per_amplicon=int(min_reads_per_amplicon),
            amplicon_imbalance_factor=float(amplicon_imbalance_factor),
        )
    elif is_shotgun_metagenomics:
        show_shotgun_plan_ui(
            usable_gb_per_sample=shotgun_usable_gb_per_sample,
            target_gb_per_sample=float(shotgun_gb_per_sample),
        )

    # Persist state to the URL.
    update_query_params(
        {
            "coverage_mode": coverage_mode,
            "variable": variable,
            "preset": preset_label,
            "region_input": region_input,
            "depth": depth,
            "samples": samples,
            "duplication": duplication,
            "on_target": on_target,
            "platform": platform_id,
            "runtime_hr": runtime_hr,
            "apply_gc_bias": apply_gc_bias,
            "gc_bias_percent": gc_bias_percent,
            "apply_fragment_model": apply_fragment_model,
            "read_filter_loss": read_filter_loss,
            "fragment_size": fragment_size,
            "read_length": read_length,
            "num_amplicons": num_amplicons,
            "amplicon_size": amplicon_size,
            "min_reads_per_amplicon": min_reads_per_amplicon,
            "amplicon_imbalance_factor": amplicon_imbalance_factor,
            "shotgun_gb_per_sample": shotgun_gb_per_sample,
            "planning_samples": planning_samples,
            "reserve_margin_pct": reserve_margin_pct,
            # ddRAD state
            "target_fraction_pct": target_fraction_pct,
            "ddrad_mode": "fraction_to_genome",
            "known_genome_input": known_genome_input,
        }
    )
