# utils/unit_parser.py

def parse_region_size(input_str: str) -> int:
    """
    Parse strings like '3.3Gb', '500 Kbp', '1.2M', '1000000' into integer bp.
    Returns size in base pairs (bp).
    """
    input_str = input_str.strip().replace(" ", "").lower()

    suffix_map = {
        "g": 1_000_000_000,
        "gb": 1_000_000_000,
        "m": 1_000_000,
        "mb": 1_000_000,
        "k": 1_000,
        "kb": 1_000,
        "bp": 1,
        "b": 1
    }

    for suffix, factor in suffix_map.items():
        if input_str.endswith(suffix):
            num_str = input_str[:-len(suffix)]
            break
    else:
        num_str = input_str
        factor = 1

    try:
        value = float(num_str)
    except ValueError:
        raise ValueError(f"Could not parse region size from input: '{input_str}'")

    return int(value * factor)

def format_region_size(bp: int, precision: int = 2) -> str:
    """
    Convert an integer bp value into a human-readable string (e.g., 3.3 Gb).
    """
    thresholds = [
        (1_000_000_000, "Gb"),
        (1_000_000, "Mb"),
        (1_000, "Kb"),
    ]

    for factor, label in thresholds:
        if bp >= factor:
            value = round(bp / factor, precision)
            return f"{value} {label}"

    return f"{bp} bp"
