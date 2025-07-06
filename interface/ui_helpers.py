# interface/ui_helpers.py

import streamlit as st
from coverage_calculator.utils.unit_parser import parse_region_size, format_region_size

from typing import Optional

def show_results_ui(
        result_placeholder,
        warning_placeholder,
        variable: str,
        result,
        label: str,
        value: str,
        delta: str,
        total_bp: float,
        num_amplicons: Optional[int] = None
    ):
    """
    Shows the results metric and any relevant warnings.
    """
    with result_placeholder:
        st.metric(label=label, value=value, delta=delta, delta_color="off", border=True)

    if variable == "Samples per flow cell" and result < 1:
        warning_placeholder.warning("Sequencing output is too low for even one sample.")
    if total_bp < 1_000_000:
        warning_placeholder.error("Effective sequencing output is extremely low.")
    # Example: add more warnings for unrealistic amplicon values
    if variable == "Samples per flow cell" and num_amplicons is not None and num_amplicons > 100_000:
        warning_placeholder.warning("Number of amplicons is very high. Is your region size correct?")

def dedup_on_target_ui(preset_values, params):
    """
    Shows duplication and on-target number inputs if Custom, else fills from preset.
    Returns: duplication, on_target
    """
    if preset_values is not None:
        # For presets, just return the preset's values (no columns needed)
        duplication = preset_values.duplication_pct
        on_target = preset_values.on_target_pct
    else:
        # For custom, show editable fields (columns)
        col_dup, col_target = st.columns(2)
        with col_dup:
            duplication = st.number_input(
                "Duplication (%)",
                min_value=0.0,
                max_value=50.0,
                value=params["duplication"],
                step=0.5,
                help="Estimated percent of duplicate reads (remove PCR/sequencing duplicates)."
            )
        with col_target:
            on_target = st.number_input(
                "On-target (%)",
                min_value=0,
                max_value=100,
                value=params["on_target"],
                step=1,
                help="Fraction of sequenced reads mapping to the intended region/target."
            )
    return duplication, on_target

def advanced_options_ui(coverage_mode: str, params):
    """
    Advanced modeling options expander.
    Returns: apply_complexity, apply_gc_bias, gc_bias_percent, apply_fragment_model, fragment_size, read_length
    """
    with st.expander("Advanced Modeling Options", expanded=False):
        if coverage_mode == "Genome-wide":
            apply_complexity = st.checkbox(
                "Model library complexity (Lander-Waterman)",
                value=params["apply_complexity"],
                help="If enabled, adjusts for reduced yield in very high-depth (repetitive) sequencing."
            )
        else:
            apply_complexity = False

        apply_gc_bias = st.checkbox(
            "Apply GC/sequence bias correction",
            value=params["apply_gc_bias"],
            help="Models loss of usable data from GC or other sequence content bias."
        )
        apply_fragment_model = st.checkbox(
            "Adjust for fragment/read length overlap",
            value=params["apply_fragment_model"],
            help="Subtracts overlapping bases when paired-end reads extend beyond the fragment."
        )

        read_filter_loss = st.slider(
            "Instrument Q-score/quality filtering loss (%)",
            min_value=0.0, max_value=20.0,
            value=params.get("read_filter_loss", 5.0),
            step=0.5,
            help="Percent of reads lost to instrument filtering (fail QC/basecalling). Typical: 3-7%."
        )

        if apply_fragment_model:
            fragment_size = st.number_input(
                "Fragment size (bp)", min_value=50, value=params["fragment_size"],
                help="Average size of sequencing fragments after library prep."
            )
            read_length = st.number_input(
                "Read length (bp)", min_value=50, value=params["read_length"],
                help="Length of each sequencing read (e.g. 150 for PE150)."
            )
        else:
            fragment_size = None
            read_length = None

        if apply_gc_bias:
            gc_bias_percent = st.slider(
                "Bias loss (%)", 0.0, 20.0, params["gc_bias_percent"],
                help="Fraction of data lost due to GC or other sequence content bias."
            )
        else:
            gc_bias_percent = 0.0

    return (apply_complexity, apply_gc_bias, gc_bias_percent,
            apply_fragment_model, fragment_size, read_length, read_filter_loss)

def preset_select_ui(coverage_mode: str, params, GENOME_WIDE_PRESETS, TARGETED_PRESETS):
    """
    Shows the preset selectbox for protocols.
    Returns: (preset_label, preset_values, active_presets)
    """
    if coverage_mode == "Genome-wide":
        active_presets = GENOME_WIDE_PRESETS
    else:
        active_presets = TARGETED_PRESETS

    preset_label_list = ["Custom"] + [preset.label for preset in active_presets.values()]
    preset_label = st.selectbox(
        "Protocol Preset",
        preset_label_list,
        index=0,
        help="Select a common protocol to auto-fill recommended parameters like region size, duplication, and on-target rate."
    )
    if preset_label != "Custom":
        preset_key = next(
            (key for key, preset in active_presets.items() if preset.label == preset_label),
            None
        )
        if preset_key is None:
            st.error("Internal error: selected preset not found.")
            st.stop()
        preset_values = active_presets[preset_key]
    else:
        preset_values = None

    return preset_label, preset_values, active_presets

def platform_selector_ui(params, PLATFORM_CONFIG):
    platform_ids = list(PLATFORM_CONFIG.keys())
    platform_names = [PLATFORM_CONFIG[pid]["name"] for pid in platform_ids]

    # Use platform from params if it matches; else fallback to first
    default_platform_id = None
    if params["platform"] in platform_ids:
        default_platform_id = params["platform"]
    else:
        for pid, pname in zip(platform_ids, platform_names):
            if params["platform"] == pname:
                default_platform_id = pid
                break
        else:
            default_platform_id = platform_ids[0]

    platform_idx = platform_ids.index(default_platform_id)
    selected_name = st.selectbox(
        "Sequencing Platform",
        options=platform_names,
        index=platform_idx
    )
    platform_id = platform_ids[platform_names.index(selected_name)]
    platform = PLATFORM_CONFIG[platform_id]
    output_bp = platform["output_bp"]

    # MinION special case (optional)
    if "MINION" in platform_id:
        runtime_hr = st.slider(
            "MinION Runtime (hrs)", 0, 72, params.get("runtime_hr", 48),
            help="For ONT MinION: expected run duration in hours."
        )
        output_bp = 3_472_222 * runtime_hr * 60
        st.caption(f"Estimated Output: {format_region_size(int(output_bp))} based on runtime")
    else:
        runtime_hr = params.get("runtime_hr", 48)

    output_bp = platform["output_bp"]

    return platform_id, platform, output_bp, runtime_hr

def region_size_input_ui(
    coverage_mode: str,
    variable: str,
    preset_values,
    params,
    region_input: str
):
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
                default_amplicon_size = round(preset_values.region_bp / default_num_amplicons)
            else:
                default_num_amplicons = num_amplicons
                default_amplicon_size = amplicon_size

            col_n_amp, col_amp_size = st.columns(2)
            with col_n_amp:
                num_amplicons = st.number_input(
                    "Number of Amplicons",
                    min_value=1,
                    value=default_num_amplicons,
                    step=10,
                    key="num_amplicons_input",
                    help="Total number of unique amplicons in your panel."
                )
            with col_amp_size:
                amplicon_size = st.number_input(
                    "Avg Amplicon Size (bp)",
                    min_value=50,
                    value=default_amplicon_size,
                    step=25,
                    key="amplicon_size_input",
                    help="Average size (in bp) of each amplicon."
                )
            region_size = num_amplicons * amplicon_size
            region_input = f"{region_size} bp"
            st.caption(f"Total region size: {format_region_size(region_size)}")
        else:
            region_input = st.text_input(
                "Genome/Region Size",
                value=region_input,
                disabled=variable == "Genome size",
                help="Total size of region to cover (e.g. '3.3 Gb', '50 Mb', '1200000')."
            )
            try:
                region_size = parse_region_size(region_input) if region_input else 1
            except Exception:
                st.warning("Could not parse region size. Enter a value like '3.3 Gb' or '5000000'.")
                region_size = 1

    return region_size, region_input, num_amplicons, amplicon_size