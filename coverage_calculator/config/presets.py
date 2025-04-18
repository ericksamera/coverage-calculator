# coverage_calculator/config/presets.py

from dataclasses import dataclass

@dataclass
class ProtocolPreset:
    label: str
    region_bp: int
    duplication_pct: float
    on_target_pct: float
    amplicon_count: int = None

PRESETS = {
    "WGS (Human)": ProtocolPreset("WGS (Human)", 3_300_000_000, 2.5, 100),
    "Exome (Human)": ProtocolPreset("Exome (Human)", 50_000_000, 15.0, 80),
    "Amplicon Panel": ProtocolPreset("Amplicon Panel", 400_000, 10.0, 90),
    "Bacterial WGS": ProtocolPreset("Bacterial WGS", 5_000_000, 2.0, 100),
}
