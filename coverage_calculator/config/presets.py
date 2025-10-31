import yaml
from dataclasses import dataclass
from typing import Optional, Dict
import os


@dataclass
class ProtocolPreset:
    label: str
    region_bp: int
    duplication_pct: float
    on_target_pct: float
    amplicon_count: Optional[int] = None


def load_presets() -> Dict[str, Dict[str, ProtocolPreset]]:
    yaml_path = os.path.join(os.path.dirname(__file__), "presets.yaml")
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)
    presets: Dict[str, Dict[str, ProtocolPreset]] = {"genome_wide": {}, "targeted": {}}
    for category in ("genome_wide", "targeted"):
        for p in config.get(category, []):
            presets[category][p["id"]] = ProtocolPreset(
                label=p["label"],
                region_bp=int(p["region_bp"]),
                duplication_pct=float(p["duplication_pct"]),
                on_target_pct=float(p["on_target_pct"]),
                amplicon_count=(
                    int(p["amplicon_count"]) if "amplicon_count" in p else None
                ),
            )
    return presets


PRESETS = load_presets()
GENOME_WIDE_PRESETS = PRESETS["genome_wide"]
TARGETED_PRESETS = PRESETS["targeted"]
