# coverage_calculator/utils/query_state.py

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import streamlit as st

from coverage_calculator.utils.config_codec import decode_config, encode_config


def safe_cast(val: Any, to_type, default: Any) -> Any:
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def _read_config_blob() -> Optional[str]:
    # Accept "config" primarily; fall back to "c" as a short alias if present.
    q = st.query_params
    return q.get("config") or q.get("c")


def load_query_params() -> Dict[str, Any]:
    """
    Read the app's query params, decode the 'config' blob if present,
    and return a normalized params dict with safe types & defaults.
    """
    encoded_config = _read_config_blob()
    params: Dict[str, Any] = {}

    if encoded_config:
        try:
            params = decode_config(encoded_config)
        except ValueError:
            st.warning(
                "⚠️ Could not parse the configuration string. "
                "It may be corrupted or incomplete."
            )
            params = {}

    return {
        "coverage_mode": params.get("coverage_mode", "Targeted Panel"),
        "variable": params.get("variable", "Samples per flow cell"),
        "preset": params.get("preset", "Custom"),
        "region_input": params.get("region_input", "3.3 Gb"),
        "depth": safe_cast(params.get("depth"), int, 30),
        "samples": safe_cast(params.get("samples"), int, 1),
        "duplication": safe_cast(params.get("duplication"), float, 2.5),
        "on_target": safe_cast(params.get("on_target"), int, 85),
        "platform": params.get("platform", "NovaSeq 6000"),
        "runtime_hr": safe_cast(params.get("runtime_hr"), int, 48),
        "apply_complexity": params.get("apply_complexity", False),
        "apply_gc_bias": params.get("apply_gc_bias", False),
        "gc_bias_percent": safe_cast(params.get("gc_bias_percent"), float, 5.0),
        "apply_fragment_model": params.get("apply_fragment_model", False),
        "read_filter_loss": safe_cast(params.get("read_filter_loss"), float, 5.0),
        "fragment_size": safe_cast(params.get("fragment_size"), int, 300),
        "read_length": safe_cast(params.get("read_length"), int, 150),
        "num_amplicons": safe_cast(params.get("num_amplicons"), int, 1380),
        "amplicon_size": safe_cast(params.get("amplicon_size"), int, 175),
        # ddRAD
        "target_fraction_pct": safe_cast(params.get("target_fraction_pct"), float, 2.0),
        "ddrad_mode": params.get("ddrad_mode", "fraction_to_genome"),
        "known_genome_input": params.get("known_genome_input", "3.3 Gb"),
    }


def update_query_params(params: Dict[str, Any]) -> None:
    """
    Persist the provided params dict into the URL as a compact 'config' blob.

    Guard against redundant writes to avoid unnecessary reruns and URL churn.
    """
    encoded = encode_config(params)
    if st.query_params.get("config") != encoded:
        st.query_params["config"] = encoded


def share_and_load_ui(params: Optional[Dict[str, Any]] = None) -> None:
    """
    Sidebar/inline panel for sharing and loading app state.

    - Shows a copyable code (encoded config).
    - Offers a JSON download of the current state.
    - Lets the user paste an encoded code or upload a JSON to load, then reruns.
    """
    with st.expander("Share / Load configuration", expanded=False):
        # If the caller passed a params snapshot for *this* run, prefer it.
        # Otherwise fall back to whatever is in the URL right now.
        if params is not None:
            current_code = encode_config(params)
        else:
            current_code = _read_config_blob() or encode_config({})

        st.code(current_code)

        # Also offer a JSON download of the decoded state
        try:
            decoded = decode_config(current_code)
        except Exception:
            decoded = params or {}

        st.download_button(
            "Download config.json",
            data=json.dumps(decoded, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="coverage-config.json",
            mime="application/json",
            help="Save the current configuration as a JSON file.",
        )

        st.divider()

        left, right = st.columns(2)
        with left:
            pasted = st.text_area(
                "Paste a share code to load",
                placeholder="cc2.0123abcd....",
                height=100,
            )
            if st.button("Load from code"):
                code = pasted.strip()
                if not code:
                    st.info("Paste a code first.")
                else:
                    try:
                        _ = decode_config(code)  # validate
                        st.query_params["config"] = code
                        st.rerun()
                    except ValueError:
                        st.error(
                            "That code couldn't be parsed. Make sure you pasted the whole string."
                        )

        with right:
            uploaded = st.file_uploader("…or upload a configuration JSON", type=["json"])
            if uploaded is not None:
                try:
                    data = json.load(uploaded)
                    code = encode_config(data)
                    st.query_params["config"] = code
                    st.rerun()
                except Exception:
                    st.error("Couldn't read that file. Is it valid JSON?")
