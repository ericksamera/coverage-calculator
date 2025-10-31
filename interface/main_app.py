import streamlit as st

from coverage_calculator.utils.unit_parser import format_region_size
from coverage_calculator.utils.query_state import (
    load_query_params,
    update_query_params,
)
from coverage_calculator.calculator.coverage_model import CoverageCalculator
from coverage_calculator.config.platforms import PLATFORM_CONFIG
from coverage_calculator.config.presets import GENOME_WIDE_PRESETS, TARGETED_PRESETS
from coverage_calculator.calculator.modeling import (
    lander_waterman_effective_coverage,
    adjust_for_gc_bias,
    adjust_for_fragment_overlap,
)

from interface.ui_helpers import (
    show_results_ui,
    dedup_on_target_ui,
    region_size_input_ui,
    platform_selector_ui,
    preset_select_ui,
    advanced_options_ui,
    render_math_explainer,
)


def run():
    params = load_query_params()
    st.title("Sequencing Coverage Calculator")

    result_placeholder = st.empty()
    warning_placeholder = st.empty()

    # Load initial state from query or use defaults
    region_input = params.get("region_input", "3.3 Gb")
    num_amplicons = params.get("num_amplicons", 0)
    amplicon_size = params.get("amplicon_size", 0)

    col_cov, col_var = st.columns(2)
    with col_cov:
        coverage_mode = st.radio(
            "Coverage Mode",
            ["Genome-wide", "Targeted Panel"],
            help=(
                "Choose 'Genome-wide' for whole-genome or exome sequencing. "
                "Use 'Targeted Panel' for targeted-amplicon."
            ),
            index=["Genome-wide", "Targeted Panel"].index(params["coverage_mode"]),
        )

    with col_var:
        variable = st.radio(
            "Variable to calculate:",
            ["Samples per flow cell", "Depth", "Genome size"],
            help="Pick which variable you'd like to solve for, given your other inputs.",
            index=["Samples per flow cell", "Depth", "Genome size"].index(
                params["variable"]
            ),
        )

    # --- Preset selection based on mode ---
    col_preset, col_settings = st.columns(2)
    with col_preset:
        preset_label, preset_values, active_presets = preset_select_ui(
            coverage_mode, params, GENOME_WIDE_PRESETS, TARGETED_PRESETS
        )

    if preset_values is not None:
        duplication = preset_values.duplication_pct
        on_target = preset_values.on_target_pct
        if coverage_mode == "Genome-wide":
            region_input = format_region_size(preset_values.region_bp)
        else:
            num_amplicons = preset_values.amplicon_count or 1
            amplicon_size = round(preset_values.region_bp / num_amplicons)
            region_input = f"{num_amplicons * amplicon_size} bp"
    else:
        duplication, on_target = dedup_on_target_ui(preset_values, params)

    col_size, col_depth, col_samples = st.columns(3)

    with col_size:
        region_size, region_input, num_amplicons, amplicon_size = region_size_input_ui(
            coverage_mode, variable, preset_values, params, region_input
        )

    with col_depth:
        with st.container(border=True):
            depth = st.number_input(
                "Depth (X)",
                value=params["depth"],
                disabled=variable == "Depth",
                step=5,
            )
            if coverage_mode == "Targeted Panel" and depth < 100:
                st.info(
                    "For amplicon-based panels (AmpliSeq), sequencing depths of 500–1000X "
                    "are typical. For Metagenomics, aim for greater than 10000X."
                )
            if coverage_mode == "Genome-wide" and depth < 20:
                st.info("Whole genome sequencing usually aims for at least 20X.")

    with col_samples:
        with st.container(border=True):
            samples = st.number_input(
                "Samples",
                value=params["samples"],
                step=1,
                disabled=variable == "Samples per flow cell",
            )

    platform_id, platform, output_bp, runtime_hr = platform_selector_ui(
        params, PLATFORM_CONFIG
    )

    (
        apply_complexity,
        apply_gc_bias,
        gc_bias_percent,
        apply_fragment_model,
        fragment_size,
        read_length,
        read_filter_loss,
    ) = advanced_options_ui(coverage_mode, params)

    # --- Calculations (build effective output) ---
    # Start from the platform output (may be runtime-adjusted for MinION).
    total_bp = output_bp

    # Instrument read filtering (Q-score loss)
    if read_filter_loss > 0:
        total_bp *= 1 - read_filter_loss / 100.0

    # Fragment overlap
    if apply_fragment_model:
        fsafe = fragment_size if fragment_size is not None else 0
        rsafe = read_length if read_length is not None else 0
        total_bp = adjust_for_fragment_overlap(total_bp, rsafe, fsafe)

    # Library complexity (Lander–Waterman)
    if apply_complexity:
        total_bp = lander_waterman_effective_coverage(region_size, total_bp)

    # GC / sequence bias
    if apply_gc_bias:
        total_bp = adjust_for_gc_bias(total_bp, gc_bias_percent / 100.0)

    # Calculator with effective-yield terms wired in
    calc = CoverageCalculator(
        region_size_bp=region_size,
        depth=depth,
        samples=samples,
        output_bp=total_bp,
        duplication_pct=duplication,  # <— now honored
        on_target_pct=on_target,  # <— now honored
    )

    if variable == "Samples per flow cell":
        result = calc.calc_samples_per_flow_cell()
        label = "Samples per Flow Cell"
        value = f"{result:.1f}"
        delta = (
            f"at {depth:.1f}X coverage per amplicon (based on {num_amplicons} "
            f"amplicons averaging {amplicon_size} bp each) using the "
            f"{platform['name']} platform."
            if coverage_mode == "Targeted Panel"
            else f"at {depth:.1f}X genome-wide"
        )

    elif variable == "Depth":
        result = calc.calc_depth()
        label = "Estimated Depth"
        value = f"{result:.1f}X"
        delta = (
            f"Per amplicon across {samples} samples"
            if coverage_mode == "Targeted Panel"
            else f"Genome-wide across {samples} samples using {platform['name']}"
        )

    elif variable == "Genome size":
        result = calc.calc_genome_size()
        label = "Supported Region Size"
        value = format_region_size(int(result))
        delta = f"at {depth:.1f}X depth for {samples} samples"

    else:
        result = 0
        label = "Result"
        value = "N/A"
        delta = ""

    show_results_ui(
        result_placeholder,
        warning_placeholder,
        variable,
        result,
        label,
        value,
        delta,
        total_bp,
        num_amplicons=num_amplicons,
    )

    # --- NEW: “How the math works” explainer at the bottom ---
    render_math_explainer(
        variable=variable,
        region_size_bp=region_size,
        depth=float(depth),
        samples=int(samples),
        platform_name=platform["name"],
        base_output_bp=float(output_bp),
        total_bp_after=float(total_bp),
        duplication_pct=float(duplication),
        on_target_pct=float(on_target),
        read_filter_loss=float(read_filter_loss),
        apply_fragment_model=apply_fragment_model,
        fragment_size=fragment_size,
        read_length=read_length,
        applied_complexity=apply_complexity,
        applied_gc_bias=apply_gc_bias,
        gc_bias_percent=float(gc_bias_percent),
        result_value=float(result),
    )

    # Persist state to the URL
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
            "apply_complexity": apply_complexity,
            "apply_gc_bias": apply_gc_bias,
            "gc_bias_percent": gc_bias_percent,
            "apply_fragment_model": apply_fragment_model,
            "read_filter_loss": read_filter_loss,
            "fragment_size": fragment_size,
            "read_length": read_length,
            "num_amplicons": num_amplicons,
            "amplicon_size": amplicon_size,
        }
    )
