# interface/main_app.py

from __future__ import annotations

import streamlit as st

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
from coverage_calculator.utils.unit_parser import (
    format_region_size,
    parse_region_size,
)
from interface.ui_helpers import (
    advanced_options_ui,
    ddrad_config_ui,
    dedup_on_target_ui,
    platform_selector_ui,
    preset_select_ui,
    region_size_input_ui,
    show_results_ui,
)
from interface.math_explainer import render_math_explainer


def run() -> None:
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
    col_preset, _col_settings = st.columns(2)
    with col_preset:
        preset_label, preset_values, _active_presets = preset_select_ui(
            coverage_mode, params, GENOME_WIDE_PRESETS, TARGETED_PRESETS
        )

    if preset_values is not None:
        duplication = preset_values.duplication_pct
        on_target = preset_values.on_target_pct
        if coverage_mode == "Genome-wide":
            # For ddRAD we keep the free-form inputs (fraction panel handles it)
            if getattr(preset_values, "target_fraction_pct", None) is None:
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

        # ddRAD panel appears only in Genome-wide + Genome size + ddRAD preset
        ddrad_enabled, ddrad_mode, target_fraction_pct, known_genome_input = (
            ddrad_config_ui(
                preset_values=preset_values,
                params=params,
                show_panel=(
                    coverage_mode == "Genome-wide"
                    and variable == "Genome size"
                    and preset_values is not None
                    and getattr(preset_values, "target_fraction_pct", None) is not None
                ),
            )
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
                    "are typical. For Metagenomics, aim for >10,000X."
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

    # --- Effective output stages (single source of truth) ---
    safe_region_for_model = max(1, int(region_size))
    stages: EffectiveOutputStages = compute_effective_output(
        base_output_bp=float(output_bp),
        read_filter_loss_pct=float(read_filter_loss),
        apply_fragment_model=apply_fragment_model,
        fragment_size=fragment_size,
        read_length=read_length,
        apply_complexity=apply_complexity,
        apply_gc_bias=apply_gc_bias,
        gc_bias_pct=float(gc_bias_percent),
        region_size_bp=safe_region_for_model,
        duplication_pct=float(duplication),
        on_target_pct=float(on_target),
    )
    total_bp = stages.o4  # Effective output after all stages

    # --- Calculator using the effective output + eff fraction ---
    calc = CoverageCalculator(
        region_size_bp=safe_region_for_model,
        depth=depth,
        samples=samples,
        output_bp=total_bp,
        duplication_pct=duplication,
        on_target_pct=on_target,
    )

    # --- Prepare result metric ---
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

    else:  # "Genome size"
        target_region_bp = calc.calc_genome_size()  # G_target at depth D across S
        if ddrad_enabled:
            if ddrad_mode == "fraction_to_genome":
                f = max(0.0001, float(target_fraction_pct) / 100.0)
                result = target_region_bp / f
                label = "Supported Whole-Genome Size (ddRAD)"
                value = format_region_size(int(result))
                delta = (
                    f"from target fraction {target_fraction_pct:.2f}% at {depth:.1f}X "
                    f"across {samples} samples"
                )
            else:
                # Solve % from known genome size
                try:
                    known_genome_bp = parse_region_size(known_genome_input)
                except Exception:
                    known_genome_bp = 0
                frac_pct = (
                    (target_region_bp / known_genome_bp) * 100.0
                    if known_genome_bp > 0
                    else 0.0
                )
                result = max(0.0, min(100.0, frac_pct))
                label = "Target fraction of genome (ddRAD)"
                value = f"{result:.2f}%"
                delta = (
                    f"given known genome {format_region_size(known_genome_bp)} at "
                    f"{depth:.1f}X across {samples} samples"
                )
        else:
            # Not ddRAD: report the region size directly
            result = target_region_bp
            label = "Supported Region Size"
            value = format_region_size(int(result))
            delta = f"at {depth:.1f}X depth for {samples} samples"

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

    # “How the math works” explainer
    known_genome_bp_val = None
    if ddrad_enabled and ddrad_mode == "genome_to_fraction":
        try:
            known_genome_bp_val = parse_region_size(known_genome_input)
        except Exception:
            known_genome_bp_val = None

    render_math_explainer(
        variable=variable,
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
        applied_complexity=apply_complexity,
        applied_gc_bias=apply_gc_bias,
        gc_bias_percent=float(gc_bias_percent),
        result_value=float(result) if isinstance(result, (int, float)) else 0.0,
        ddrad_enabled=ddrad_enabled,
        ddrad_mode=ddrad_mode,
        target_fraction_pct=float(target_fraction_pct),
        known_genome_bp=known_genome_bp_val,
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
            # ddRAD state
            "target_fraction_pct": target_fraction_pct,
            "ddrad_mode": ddrad_mode,
            "known_genome_input": known_genome_input,
        }
    )
