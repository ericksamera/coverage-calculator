# Coverage Calculator

A Streamlit-based calculator for planning sequencing experiments.
Easily estimate samples per flowcell, coverage depth, or region size for any platform and protocol.

## Features
- Genome-wide or targeted panel calculations
- Preset protocols (WGS, exome, panels) and sequencing platforms (MiSeq, MinION, etc.)
- Handles sample number, depth, genome/target size, duplication, and more
- Advanced options for bias, fragment overlap, library complexity, and read filtering
- No spreadsheet needed—results and warnings update instantly

## Customizing
- Edit protocols/panels: coverage_calculator/config/presets.yaml
- Edit platforms: coverage_calculator/config/platforms.yaml