import streamlit as st
import json

from coverage_calculator.utils.unit_parser import parse_region_size, format_region_size
from coverage_calculator.utils.query_state import (
    load_query_params, update_query_params, encode_config, decode_config
)
from coverage_calculator.calculator.coverage_model import CoverageCalculator
from coverage_calculator.config.platforms import Platform, PLATFORM_OUTPUT
from coverage_calculator.config.presets import PRESETS
from coverage_calculator.calculator.modeling import (
    lander_waterman_effective_coverage,
    adjust_for_gc_bias,
    adjust_for_fragment_overlap,
)

def run():
    params = load_query_params()
    st.title("Sequencing Coverage Calculator")

    # -- Paste Config Modal
    @st.dialog("Paste Configuration Code")
    def paste_config_dialog():
        config_input = st.text_area("Paste configuration string here (base64-encoded):", height=150)
        if st.button("Apply Configuration"):
            config = decode_config(config_input.strip())
            if config:
                for k, v in config.items():
                    st.session_state[k] = v
                st.success("✅ Configuration applied. Reloading...")
                st.rerun()

    if st.button("🧩 Paste Configuration Code"):
        paste_config_dialog()

    result_placeholder = st.empty()
    result_dl_placeholder = st.empty()
    warning_placeholder = st.empty()

    # Load initial state from query or use defaults
    region_input = params.get("region_input", "3.3 Gb")
    coverage_mode = st.segmented_control(
        "Coverage Mode", ["Genome-wide", "Targeted Panel"],
        help="Choose 'Genome-wide' for whole-genome or exome sequencing. Use 'Targeted Panel' for targeted-amplicon.",
        default=params["coverage_mode"])

    variable = st.segmented_control(
        "Variable to calculate:", ["Samples per flow cell", "Depth", "Genome size"],
        help="Pick which variable you'd like to solve for, given your other inputs.",
        default=params["variable"])

    col_preset, col_settings = st.columns(2)
    with col_preset: 
        preset = st.selectbox(
            "Protocol Preset", ["Custom"] + list(PRESETS), index=0,
            help="Select a common protocol to auto-fill recommended parameters like region size, duplication, and on-target rate.")

    if preset != "Custom":
        preset_values = PRESETS[preset]
        duplication = preset_values.duplication_pct
        on_target = preset_values.on_target_pct
        if coverage_mode == "Genome-wide":
            region_input = format_region_size(preset_values.region_bp)
        else:
            num_amplicons = preset_values.amplicon_count or 1380
            amplicon_size = round(preset_values.region_bp / num_amplicons)
            region_input = f"{num_amplicons * amplicon_size} bp"
    else:
        col_dup, col_target = st.columns(2)
        with col_dup:
            duplication = st.number_input("Duplication (%)", min_value=0.0, max_value=50.0, value=params["duplication"], step=0.5)
        with col_target:
            on_target = st.number_input("On-target (%)", min_value=0, max_value=100, value=params["on_target"], step=1)

    col_size, col_depth, col_samples = st.columns(3)

    with col_size:
        with st.container(border=True):
            if coverage_mode == "Targeted Panel":
                col_n_amp, col_amp_size = st.columns(2)
                with col_n_amp:
                    num_amplicons = st.number_input("Number of Amplicons", min_value=1, value=params["num_amplicons"], step=10)
                with col_amp_size:
                    amplicon_size = st.number_input("Avg Amplicon Size (bp)", min_value=50, value=params["amplicon_size"], step=25)
                region_size = num_amplicons * amplicon_size
                region_input = f"{region_size} bp"
                st.caption(f"Total region size: {format_region_size(region_size)}")
            else:
                region_input = st.text_input("Genome/Region Size", value=region_input, disabled=variable == "Genome size")
                region_size = parse_region_size(region_input) if region_input else 1

    with col_depth:
        with st.container(border=True): 
            depth = st.number_input("Depth (X)", value=params["depth"], disabled=variable == "Depth", step=5)
            if coverage_mode == "Targeted Panel" and depth < 100:
                st.info("For amplicon-based panels, sequencing depths of 500–1000X are typical.")
            if coverage_mode == "Genome-wide" and depth < 20:
                st.info("Whole genome sequencing usually aims for at least 20X.")

    with col_samples:
        with st.container(border=True):
            samples = st.number_input("Samples", value=params["samples"], step=1, disabled=variable == "Samples per flow cell")

    platform = st.selectbox("Sequencing Platform", options=list(Platform), format_func=lambda p: p.value, index=0)
    output_bp = PLATFORM_OUTPUT[platform]

    if platform == Platform.MINION:
        runtime_hr = st.slider("MinION Runtime (hrs)", 0, 72, params["runtime_hr"])
        output_bp = 3_472_222 * runtime_hr * 60
        st.caption(f"Estimated Output: {format_region_size(int(output_bp))} based on runtime")
    else:
        runtime_hr = params["runtime_hr"]

    with st.expander("Advanced Modeling Options", expanded=False):
        if coverage_mode == "Genome-wide":
            apply_complexity = st.checkbox("Model library complexity (Lander-Waterman)", value=params["apply_complexity"])
        else:
            apply_complexity = False

        apply_gc_bias = st.checkbox("Apply GC/sequence bias correction", value=params["apply_gc_bias"])
        apply_fragment_model = st.checkbox("Adjust for fragment/read length overlap", value=params["apply_fragment_model"])

        if apply_fragment_model:
            fragment_size = st.number_input("Fragment size (bp)", min_value=50, value=params["fragment_size"])
            read_length = st.number_input("Read length (bp)", min_value=50, value=params["read_length"])
        else:
            fragment_size = None
            read_length = None

        if apply_gc_bias:
            gc_bias_percent = st.slider("Bias loss (%)", 0.0, 20.0, params["gc_bias_percent"])
        else:
            gc_bias_percent = 0.0

    # --- Calculations ---
    usable_fraction = (1 - duplication / 100) * (on_target / 100)
    total_bp = output_bp

    if apply_fragment_model:
        total_bp = adjust_for_fragment_overlap(total_bp, read_length, fragment_size)
    if apply_complexity:
        total_bp = lander_waterman_effective_coverage(region_size, total_bp)
    if apply_gc_bias:
        total_bp = adjust_for_gc_bias(total_bp, gc_bias_percent / 100)

    calc = CoverageCalculator(
        region_size_bp=region_size,
        depth=depth,
        samples=samples,
        output_bp=total_bp,
        duplication_pct=0,
        on_target_pct=100,
    )

    if variable == "Samples per flow cell":
        result = calc.calc_samples_per_flow_cell()
        label = "Samples per Flow Cell"
        value = f"{result:.1f}"
        delta = f"at {depth:.1f}X per amplicon (across {num_amplicons} amplicons)" if coverage_mode == "Targeted Panel" else f"at {depth:.1f}X genome-wide"

    elif variable == "Depth":
        result = calc.calc_depth()
        label = "Estimated Depth"
        value = f"{result:.1f}X"
        delta = f"Per amplicon across {samples} samples" if coverage_mode == "Targeted Panel" else f"Genome-wide across {samples} samples"

    elif variable == "Genome size":
        result = calc.calc_genome_size()
        label = "Supported Region Size"
        value = format_region_size(int(result))
        delta = f"at {depth:.1f}X depth for {samples} samples"

    output_text = f"{label}: {value} ({delta})"

    with result_placeholder:
        st.metric(label=label, value=value, delta=delta, delta_color="off", border=True)

    if variable == "Samples per flow cell" and result < 1:
        warning_placeholder.warning("Sequencing output is too low for even one sample.")
    if variable == "Depth" and result > 1000:
        warning_placeholder.warning("Depth exceeds 1000X.")
    if total_bp < 1_000_000:
        warning_placeholder.error("Effective sequencing output is extremely low.")

    update_query_params({
        "coverage_mode": coverage_mode,
        "variable": variable,
        "preset": preset,
        "region_input": region_input,
        "depth": depth,
        "samples": samples,
        "duplication": duplication,
        "on_target": on_target,
        "platform": platform.value,
        "runtime_hr": runtime_hr,
        "apply_complexity": apply_complexity,
        "apply_gc_bias": apply_gc_bias,
        "gc_bias_percent": gc_bias_percent,
        "apply_fragment_model": apply_fragment_model,
        "fragment_size": fragment_size,
        "read_length": read_length,
        "num_amplicons": num_amplicons,
        "amplicon_size": amplicon_size,
    })
