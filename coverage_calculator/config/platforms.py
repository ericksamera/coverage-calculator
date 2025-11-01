# coverage_calculator/config/platforms.py

from __future__ import annotations

import os
from typing import Any, Dict

import yaml

from coverage_calculator.utils.unit_parser import parse_region_size


def load_platforms() -> Dict[str, Dict[str, Any]]:
    """
    Load platform definitions from platforms.yaml.
    Returns a mapping of platform_id -> metadata.
    """
    yaml_path = os.path.join(os.path.dirname(__file__), "platforms.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    platforms: Dict[str, Dict[str, Any]] = {}
    for p in config["platforms"]:
        platforms[p["id"]] = {
            "name": p["name"],
            "output_bp": parse_region_size(p["output"]),
        }
    return platforms


PLATFORM_CONFIG: Dict[str, Dict[str, Any]] = load_platforms()
