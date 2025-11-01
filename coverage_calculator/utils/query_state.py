# coverage_calculator/utils/query_state.py

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from coverage_calculator.utils.config_codec import (
    decode_config,
    encode_config,
)


def safe_cast(val: Any, to_type, default: Any) -> Any:
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def load_query_params() -> Dict[str, Any]:
    """
    Read the app's query params, decode the 'config' blob if present,
    and return a normalized params dict with safe types & defaults.
    """
    q = st.query_params
    encoded_config = q.get("config")
    params: Dict[str, Any] = {}

    if encoded_config:
        try:
            params = decode_config(encoded_config)
        except ValueError:
            st.warning("⚠️ Could not parse the configuration string.")
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
    """
    encoded = encode_config(params)
    st.query_params["config"] = encoded
