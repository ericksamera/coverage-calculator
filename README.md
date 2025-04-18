# Sequencing Coverage Calculator

A Streamlit-based app to estimate sequencing coverage metrics such as:

- Samples per flow cell  
- Depth per sample  
- Supported region size  

Supports both **genome-wide** and **targeted panel** sequencing.

## Features

- Platform presets for MiSeq, MinION, NovaSeq, etc.
- Protocol presets (e.g. AmpliSeq-style panels)
- Modeling options:  
  - Lander-Waterman library complexity  
  - GC bias  
  - Fragment/read overlap
- Base64-encoded config sharing (via URL or paste)
- Live warnings and result formatting
- Exportable config string for reproducibility


## Example Use Cases
- AmpliSeq panel planning
- WGS depth estimation
- Flow cell sample budgeting