# coverage_calculator/config/platforms.py

import yaml
from enum import Enum
from typing import Dict, Any
from coverage_calculator.utils.unit_parser import parse_region_size
import os

class Platform(str, Enum):
    MISEQ_V2_NANO_500 = "MiSeq v2 Nano (2x250)"
    MISEQ_V2_NANO_300 = "MiSeq v2 Nano (2x150)"
    MISEQ_V2_MICRO_300 = "MiSeq v2 Micro (2x150)"
    MISEQ_V2_50 = "MiSeq v2 (2x25)"
    MISEQ_V2_300 = "MiSeq v2 (2x150)"
    MISEQ_V2_500 = "MiSeq v2 (2x250)"
    MISEQ_V3_150 = "MiSeq v3 (2x75)"
    MISEQ_V3_600 = "MiSeq v3 (2x300)"

def load_platforms() -> Dict[str, Dict[str, Any]]:
    yaml_path = os.path.join(os.path.dirname(__file__), "platforms.yaml")
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)
    platforms: Dict[str, Dict[str, Any]] = {}
    for p in config["platforms"]:
        platforms[p["id"]] = {
            "name": p["name"],
            "output_bp": parse_region_size(p["output"])
        }
    return platforms

PLATFORM_CONFIG: Dict[str, Dict[str, Any]] = load_platforms()
