# utils/unit_parser.py

import re

_SUFFIX_MAP = {
    "gbp": 1_000_000_000,
    "gbase": 1_000_000_000,
    "gb": 1_000_000_000,
    "g": 1_000_000_000,
    "mbp": 1_000_000,
    "mbase": 1_000_000,
    "mb": 1_000_000,
    "m": 1_000_000,
    "kbp": 1_000,
    "kbase": 1_000,
    "kb": 1_000,
    "k": 1_000,
    "bp": 1,
    "b": 1,
}

# Match longer suffixes first so values like "500 Kbp" are parsed as
# 500 * 1,000, not as a malformed "500k" + "bp" split.
_SUFFIX_PATTERN = "|".join(
    re.escape(suffix) for suffix in sorted(_SUFFIX_MAP, key=len, reverse=True)
)
_REGION_SIZE_RE = re.compile(
    rf"^(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)"
    rf"(?P<suffix>{_SUFFIX_PATTERN})?$"
)


def parse_region_size(input_str: str) -> int:
    """
    Parse strings like '3.3Gb', '500 Kbp', '1.2M', '1000000', '1e6', '1.5e9' into integer bp.
    Returns size in base pairs (bp).
    Raises ValueError on bad input.

    Examples:
        '3.2Gb'   -> 3200000000
        '3.2Gbp'  -> 3200000000
        '500kb'   -> 500000
        '500 Kbp' -> 500000
        '1e6'     -> 1000000
        '1500'    -> 1500
    """
    if not input_str or not isinstance(input_str, str):
        raise ValueError("Input region size must be a non-empty string.")

    normalized_input = re.sub(r"\s+", "", input_str).lower()
    match = _REGION_SIZE_RE.fullmatch(normalized_input)
    if not match:
        raise ValueError(f"Could not parse region size from input: '{input_str}'")

    num_str = match.group("value")
    suffix = match.group("suffix") or ""
    factor = _SUFFIX_MAP.get(suffix, 1)

    try:
        # Accept both floats and scientific notation (e.g., 1e6)
        value = float(num_str)
    except Exception:
        raise ValueError(f"Could not parse region size from input: '{input_str}'")

    return int(value * factor)


def format_region_size(bp: int, precision: int = 2) -> str:
    """
    Convert an integer bp value into a human-readable string (e.g., 3.3 Gb, 500 Mb, 1500 bp).
    Rounds to the given precision for Gb/Mb/Kb.

    Examples:
        3200000000 -> '3.2 Gb'
        1500 -> '1.5 Kb'
        5 -> '5 bp'
    """
    thresholds = [
        (1_000_000_000, "Gb"),
        (1_000_000, "Mb"),
        (1_000, "Kb"),
    ]

    for factor, label in thresholds:
        if bp >= factor:
            value = round(bp / factor, precision)
            # Remove trailing .0 for whole numbers
            if value == int(value):
                value = int(value)
            return f"{value} {label}"

    return f"{bp} bp"
