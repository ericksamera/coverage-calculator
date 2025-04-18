# coverage_calculator/config/platforms.py

from enum import Enum

class Platform(str, Enum):
    MISEQ_V3 = "MiSeq v3 (2x300)"
    MISEQ_V2 = "MiSeq v2 (2x250)"
    MISEQ_NANO = "MiSeq v2 Nano (2x250)"
    MISEQ_MICRO = "MiSeq v2 Micro (2x150)"
    MINION = "MinION FLO-MIN114"

# Static outputs (bp)
PLATFORM_OUTPUT = {
    Platform.MISEQ_V3: 15_000_000_000,
    Platform.MISEQ_V2: 7_500_000_000,
    Platform.MISEQ_NANO: 600_000_000,
    Platform.MISEQ_MICRO: 2_400_000_000,
    Platform.MINION: 15_000_000_000,  # Placeholder, overridden by runtime model
}
