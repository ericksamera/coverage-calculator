# coverage_calculator/utils/config_codec.py

from __future__ import annotations

import base64
import json
from typing import Any, Dict


def encode_config(params: Dict[str, Any]) -> str:
    """
    JSON-encode then URL-safe base64-encode a params dict.
    """
    json_str = json.dumps(params, separators=(",", ":"), ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode("utf-8")).decode("ascii")


def decode_config(encoded: str) -> Dict[str, Any]:
    """
    Decode a URL-safe base64 + JSON config string.

    Returns a dict on success.
    Raises ValueError on parse errors.
    """
    if not encoded or encoded in {"null", "None"}:
        return {}

    s = encoded
    missing_padding = len(s) % 4
    if missing_padding:
        s += "=" * (4 - missing_padding)

    try:
        decoded = base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        if not isinstance(data, dict):
            raise ValueError("Decoded configuration is not a JSON object.")
        return data
    except Exception as exc:
        raise ValueError("Invalid encoded configuration string.") from exc
