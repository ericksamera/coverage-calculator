# coverage_calculator/utils/query_state.py

import streamlit as st
import json
import base64


def safe_cast(val, to_type, default):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def encode_config(params: dict) -> str:
    json_str = json.dumps(params)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_config(encoded: str) -> dict:
    try:
        if not encoded or encoded in ["null", "None"]:
            return {}
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += "=" * (4 - missing_padding)
        decoded = base64.urlsafe_b64decode(encoded.encode()).decode()
        return json.loads(decoded)
    except Exception as e:
        st.warning("⚠️ Could not parse the configuration string.")
        print(f"[decode_config error] {e}")
        return {}


def load_query_params():
    q = st.query_params
    encoded_config = q.get("config")

    if encoded_config:
        params = decode_config(encoded_config)
    else:
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
    }


def update_query_params(params: dict):
    encoded = encode_config(params)
    st.query_params["config"] = encoded
