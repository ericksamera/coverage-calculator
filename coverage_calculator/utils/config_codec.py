# coverage_calculator/utils/config_codec.py

from __future__ import annotations

import base64
import binascii
import json
import zlib
from typing import Any, Dict, Tuple


# Encoding schemes:
# - cc1: JSON -> base64url (legacy-compatible)
# - cc2: JSON -> zlib -> base64url, with CRC32 of JSON for corruption detection
_SCHEME_V1 = "cc1"
_SCHEME_V2 = "cc2"


def _b64url_encode(data: bytes) -> str:
    """Base64 URL-safe encoding without padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    """Base64 URL-safe decoding with automatic padding fix."""
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("ascii"))


def encode_config(params: Dict[str, Any], *, compress: bool = True) -> str:
    """
    Encode params as a compact, URL-safe string.

    Default (V2): 'cc2.<crc32hex>.<b64(zlib(json))>'
    Legacy (V1):  'cc1.<b64(json)>'

    - sort_keys=True for deterministic strings (nice for tests and caching)
    - ensure_ascii=False to preserve non-ASCII in JSON (still UTF-8 on the wire)
    """
    json_bytes = json.dumps(
        params, separators=(",", ":"), ensure_ascii=False, sort_keys=True
    ).encode("utf-8")

    if compress:
        blob = zlib.compress(json_bytes, level=9)
        crc = f"{binascii.crc32(json_bytes) & 0xFFFFFFFF:08x}"
        return f"{_SCHEME_V2}.{crc}.{_b64url_encode(blob)}"

    return f"{_SCHEME_V1}.{_b64url_encode(json_bytes)}"


def _try_decode_v2(s: str) -> Tuple[Dict[str, Any], bool]:
    # Expect "cc2.<crc>.<b64>"
    parts = s.split(".", 2)
    if len(parts) != 3 or parts[0] != _SCHEME_V2:
        return {}, False

    _, crc_hex, b64 = parts
    try:
        blob = _b64url_decode(b64)
        json_bytes = zlib.decompress(blob)
        calc = f"{binascii.crc32(json_bytes) & 0xFFFFFFFF:08x}"
        if crc_hex.lower() != calc:
            raise ValueError("Checksum mismatch")

        data = json.loads(json_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Decoded configuration is not a JSON object.")
        return data, True
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid encoded configuration string.") from exc


def _try_decode_v1_or_legacy(s: str) -> Dict[str, Any]:
    # Accept "cc1.<b64>" or legacy "<b64>"
    if s.startswith(f"{_SCHEME_V1}."):
        b64 = s.split(".", 1)[1]
    else:
        b64 = s
    try:
        json_bytes = _b64url_decode(b64)
        data = json.loads(json_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Decoded configuration is not a JSON object.")
        return data
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid encoded configuration string.") from exc


def decode_config(encoded: str) -> Dict[str, Any]:
    """
    Decode a configuration string produced by encode_config().

    Supports:
      - cc2.<crc>.<b64>  (compressed + checksummed)
      - cc1.<b64>        (plain JSON base64)
      - <b64>            (legacy plain JSON base64)

    Returns a dict on success; raises ValueError on failure.
    """
    if not encoded or encoded in {"null", "None"}:
        return {}

    if encoded.startswith(f"{_SCHEME_V2}."):
        data, _ = _try_decode_v2(encoded)
        return data

    return _try_decode_v1_or_legacy(encoded)
