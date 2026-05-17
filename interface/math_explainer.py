# interface/math_explainer.py
from __future__ import annotations

from typing import Optional

import streamlit as st

from coverage_calculator.calculator.amplicon_model import AmpliconPlan
from coverage_calculator.calculator.effective_output import (
    EffectiveOutputStages,
)
from coverage_calculator.calculator.run_planning import RunPlan
from coverage_calculator.utils.unit_parser import format_region_size


def render_math_explainer(
    *,
    variable: str,
    region_size_bp: int,
    depth: float,
    samples: int,
    platform_name: str,
    stages: EffectiveOutputStages,
    duplication_pct: float,
    on_target_pct: float,
    read_filter_loss: float,
    apply_fragment_model: bool,
    fragment_size: Optional[int],
    read_length: Optional[int],
    applied_gc_bias: bool,
    gc_bias_percent: float,
    result_value: float,
    # ddRAD context
    ddrad_enabled: bool = False,
    ddrad_mode: str = "fraction_to_genome",
    target_fraction_pct: float = 2.0,
    known_genome_bp: Optional[int] = None,
) -> None:
    """
    Two side-by-side sections:
      • Left: formulas & definitions (pure LaTeX)
      • Right: same formulas with numbers plugged in (also LaTeX)
    """

    def _fmt_bp_tex(x: float) -> str:
        return rf"\text{{{format_region_size(int(round(x)))}}}"

    def _pct(x: float) -> str:
        return f"{x:.2f}"

    st.divider()
    with st.expander("How the math works", expanded=False):

        st.subheader("Formulas & definitions", anchor=False)
        st.markdown(f"**Platform:** {platform_name}")

        if variable != "Genome size":
            st.latex(rf"G = \text{{{format_region_size(int(region_size_bp))}}}")

        if variable != "Depth":
            st.latex(rf"D = \text{{{depth:.1f}}}")

        if variable != "Samples per flow cell":
            st.latex(rf"S = \text{{{int(samples)} sample(s)}}")

        st.markdown("#### Effective output (bp)")
        left, right = st.columns(2)
        with left:
            st.latex(r"O_1 = O_0 \times \left(1 - \frac{q}{100}\right)")
            if apply_fragment_model:
                st.latex(r"""
O_2 =
\begin{cases}
O_1 \times (1 - r) & \text{if } 2L > F \\
O_1 & \text{otherwise}
\end{cases}
\quad\text{where}\quad
r = \frac{2L - F}{2L}
""")
            else:
                st.markdown("- **O₂:** fragment/read overlap — *not applied*")

            st.latex(r"O_3 = O_2")

            if applied_gc_bias:
                st.latex(r"O_4 = O_3 \times \left(1 - \frac{b}{100}\right)")
            else:
                st.markdown("- **O₄:** GC/sequence bias — *not applied*")
        with right:
            o0, o1, o2, o3, o4 = stages.o0, stages.o1, stages.o2, stages.o3, stages.o4

            st.latex(rf"O_0 = \text{{{format_region_size(int(o0))}}}")
            st.latex(
                rf"O_1 = O_0 \times \left(1 - \frac{{q}}{{100}}\right) = "
                rf"{_fmt_bp_tex(o0)} \times \left(1 - \frac{{{_pct(read_filter_loss)}}}{{100}}\right) "
                rf"= \mathbf{{{_fmt_bp_tex(o1)}}}"
            )

            if (
                apply_fragment_model
                and stages.overlap_applies
                and fragment_size
                and read_length
            ):
                st.latex(
                    rf"r = \frac{{2L - F}}{{2L}} = \frac{{2\times {read_length} - {fragment_size}}}{{2\times {read_length}}} = {stages.redundancy:.4f}"
                )
                st.latex(
                    rf"O_2 = O_1 \times (1 - r) = {_fmt_bp_tex(o1)} \times (1 - {stages.redundancy:.4f}) "
                    rf"= \mathbf{{{_fmt_bp_tex(o2)}}}"
                )
            elif apply_fragment_model:
                st.latex(
                    rf"O_2 = O_1 \quad (\text{{no overlap: }} 2L \le F) = \mathbf{{{_fmt_bp_tex(o2)}}}"
                )
            else:
                st.latex(
                    rf"O_2 = O_1 \quad (\text{{not applied}}) = \mathbf{{{_fmt_bp_tex(o2)}}}"
                )

            st.latex(rf"O_3 = O_2 = \mathbf{{{_fmt_bp_tex(o3)}}}")

            if applied_gc_bias:
                st.latex(
                    rf"O_4 = O_3 \times \left(1 - \frac{{b}}{{100}}\right) = {_fmt_bp_tex(o3)} \times "
                    rf"\left(1 - \frac{{{_pct(gc_bias_percent)}}}{{100}}\right) = \mathbf{{{_fmt_bp_tex(o4)}}}"
                )
            else:
                st.latex(
                    rf"O_4 = O_3 \quad (\text{{not applied}}) = \mathbf{{{_fmt_bp_tex(o4)}}}"
                )

        st.divider()
        st.markdown("#### Effective-yield fraction (no units)")
        left, right = st.columns(2)
        with left:
            st.latex(
                r"\text{eff} = \left(1 - \frac{\text{dup}}{100}\right) \times \frac{\text{on\_target}}{100}"
            )
        with right:
            st.latex(
                r"\text{eff} = \left(1 - \frac{\text{dup}}{100}\right) \times \frac{\text{on\_target}}{100}"
            )
            st.latex(
                rf"\text{{eff}} = \left(1 - \frac{{{duplication_pct:.2f}}}{{100}}\right)\times"
                rf"\frac{{{on_target_pct:.2f}}}{{100}} = \mathbf{{{stages.eff_fraction:.4f}}}"
            )

        st.divider()
        st.markdown("#### Final calculation")
        left, right = st.columns(2)
        with left:
            st.latex(
                r"\text{eff} = \left(1 - \frac{\text{dup}}{100}\right) \times \frac{\text{on\_target}}{100}"
            )
            if variable == "Samples per flow cell":
                st.latex(r"S = \dfrac{O_{\text{ext}}}{\dfrac{G \cdot D}{\text{eff}}}")
            elif variable == "Depth":
                st.latex(
                    r"D = \dfrac{\left(\dfrac{O_{\text{ext}}}{S}\right)\cdot \text{eff}}{G}"
                )
            else:
                st.latex(
                    r"G_{\text{target}} = \dfrac{\left(\dfrac{O_{\text{ext}}}{S}\right)\cdot \text{eff}}{D}"
                )
                if ddrad_enabled:
                    if ddrad_mode == "fraction_to_genome":
                        st.latex(r"G = \dfrac{G_{\text{target}}}{(f/100)}")
                    else:
                        st.latex(
                            r"f = \left(\dfrac{G_{\text{target}}}{G}\right)\times 100"
                        )
        with right:
            eff = stages.eff_fraction

            if variable == "Samples per flow cell":
                denom = (region_size_bp * depth / eff) if eff > 0 else 0.0
                st.latex(
                    rf"S = \dfrac{{O_{{\text{{ext}}}}}}{{\dfrac{{G \cdot D}}{{\text{{eff}}}}}}"
                    rf" = \dfrac{{{_fmt_bp_tex(o4)}}}{{\dfrac{{{_fmt_bp_tex(region_size_bp)} \times {depth:.1f}}}{{{eff:.4f}}}}}"
                    rf" = \mathbf{{{result_value:.1f}}}\ \text{{samples}}"
                )
                # Optional intermediate:
                st.caption(
                    f"Per-sample requirement (G·D/eff) = {format_region_size(int(denom))}."
                    if eff > 0
                    else "Per-sample requirement is undefined when eff = 0."
                )

            elif variable == "Depth":
                per_sample = (o4 / samples) if samples > 0 else 0.0
                st.latex(
                    rf"D = \dfrac{{\left(\dfrac{{O_{{\text{{ext}}}}}}{{S}}\right)\cdot \text{{eff}}}}{{G}}"
                    rf" = \dfrac{{\left(\dfrac{{{_fmt_bp_tex(o4)}}}{{{samples}}}\right)\cdot {eff:.4f}}}{{{_fmt_bp_tex(region_size_bp)}}}"
                    rf" = \mathbf{{{result_value:.1f}}} \text{{X}}"
                )
                st.caption(
                    f"Per-sample output = {format_region_size(int(per_sample))}."
                )

            else:  # Genome size mode
                g_target = (
                    ((o4 / max(1, samples)) * eff / max(1e-9, depth))
                    if eff > 0
                    else 0.0
                )
                st.latex(
                    rf"G_{{\text{{target}}}} = \dfrac{{\left(\dfrac{{O_{{\text{{ext}}}}}}{{S}}\right)\cdot \text{{eff}}}}{{D}}"
                    rf" = \dfrac{{\left(\dfrac{{{_fmt_bp_tex(o4)}}}{{{samples}}}\right)\cdot {eff:.4f}}}{{{depth:.1f}}}"
                    rf" = \mathbf{{{_fmt_bp_tex(g_target)}}}"
                )

                if ddrad_enabled:
                    if ddrad_mode == "fraction_to_genome":
                        st.latex(
                            rf"G = \dfrac{{G_{{\text{{target}}}}}}{{(f/100)}} = \dfrac{{{_fmt_bp_tex(g_target)}}}{{({target_fraction_pct:.2f}\%/100)}}"
                            rf" = \mathbf{{{_fmt_bp_tex(result_value)}}}"
                        )
                    else:
                        # f = (G_target / G) × 100
                        g_known = known_genome_bp or 0
                        st.latex(
                            rf"f = \left(\dfrac{{G_{{\text{{target}}}}}}{{G}}\right)\times 100"
                            rf" = \left(\dfrac{{{_fmt_bp_tex(g_target)}}}{{{_fmt_bp_tex(g_known)}}}\right)\times 100"
                            rf" = \mathbf{{{result_value:.2f}}}\%"
                        )
        st.caption(
            "Values above reuse the same math as the calculator; numbers are rounded "
            "for readability."
        )


def render_amplicon_math_explainer(
    *,
    variable: str,
    plan: AmpliconPlan,
    num_amplicons: int,
    amplicon_size_bp: int,
    min_reads_per_amplicon: int,
    amplicon_imbalance_factor: float,
    samples: int,
    output_bp: float,
    eff_fraction: float,
    result_value: float,
) -> None:
    """Math explainer for amplicon read-count planning."""

    st.divider()
    with st.expander("How the amplicon math works", expanded=False):
        unit = plan.read_unit_label
        st.markdown("#### Amplicon read-count model")
        st.latex(r"A = \text{number of amplicons}")
        st.latex(r"R_{min} = \text{minimum usable read units per amplicon}")
        st.latex(r"I = \text{amplicon imbalance factor}")
        st.latex(r"B = \text{bases per read unit}")
        st.latex(r"\text{eff} = (1 - \text{dup}/100)\times(\text{on-target}/100)")

        st.markdown("#### Values")
        st.markdown(
            f"A = **{num_amplicons:,}**, average amplicon size = "
            f"**{amplicon_size_bp:,} bp**, B = **{plan.bases_per_unit:,} bp per {unit[:-1] if unit.endswith('s') else unit}**, "
            f"R_min = **{min_reads_per_amplicon:,}**, I = **{amplicon_imbalance_factor:.2f}**, "
            f"eff = **{eff_fraction:.4f}**."
        )

        if variable == "Samples per flow cell":
            st.latex(
                r"S = \dfrac{O}{\left(A\times R_{min}\times I\times B\right) / \text{eff}}"
            )
            st.latex(
                rf"S = \dfrac{{{format_region_size(int(output_bp))}}}{{"
                rf"({num_amplicons}\times {min_reads_per_amplicon}\times {amplicon_imbalance_factor:.2f}\times {plan.bases_per_unit})/{eff_fraction:.4f}}}"
                rf" = \mathbf{{{result_value:.1f}}}\ \text{{samples}}"
            )
        elif variable == "Depth":
            st.latex(r"R_{amp} = \dfrac{(O/S)/B\times \text{eff}}{A\times I}")
            st.latex(
                rf"R_{{amp}} = \dfrac{{({format_region_size(int(output_bp))}/{samples})/{plan.bases_per_unit}\times {eff_fraction:.4f}}}{{{num_amplicons}\times {amplicon_imbalance_factor:.2f}}}"
                rf" = \mathbf{{{result_value:.0f}}}\ \text{{{unit}/amplicon}}"
            )
        else:
            st.latex(
                r"A_{supported} = \dfrac{(O/S)/B\times \text{eff}}{R_{min}\times I}"
            )
            supported_amplicons = result_value / max(1, amplicon_size_bp)
            st.latex(
                rf"A_{{supported}} = \dfrac{{({format_region_size(int(output_bp))}/{samples})/{plan.bases_per_unit}\times {eff_fraction:.4f}}}{{{min_reads_per_amplicon}\times {amplicon_imbalance_factor:.2f}}}"
                rf" = \mathbf{{{supported_amplicons:.0f}}}\ \text{{amplicons}}"
            )
            st.caption(
                f"Supported panel size = {supported_amplicons:.0f} amplicons × "
                f"{amplicon_size_bp:,} bp ≈ {format_region_size(int(result_value))}."
            )


def render_shotgun_math_explainer(
    *,
    variable: str,
    target_gb_per_sample: float,
    usable_gb_per_sample: float,
    samples: int,
    output_bp: float,
    eff_fraction: float,
    result_value: float,
) -> None:
    """Math explainer for shotgun metagenomics data-volume planning."""

    st.divider()
    with st.expander("How the shotgun metagenomics math works", expanded=False):
        st.markdown("#### Data-volume model")
        st.latex(r"O_{usable} = O \times \text{eff}")
        st.latex(r"T = \text{target usable data per sample in Gb}")
        st.latex(
            rf"O_{{usable}} = {format_region_size(int(output_bp))}\times {eff_fraction:.4f} = "
            rf"\mathbf{{{format_region_size(int(output_bp * eff_fraction))}}}"
        )

        if variable == "Samples per flow cell":
            st.latex(r"S = \dfrac{O_{usable}}{T\times 10^9}")
            st.latex(
                rf"S = \dfrac{{{format_region_size(int(output_bp * eff_fraction))}}}{{{target_gb_per_sample:.2f}\times 10^9}}"
                rf" = \mathbf{{{result_value:.1f}}}\ \text{{samples}}"
            )
        else:
            st.latex(r"\text{Gb/sample} = \dfrac{O_{usable}/S}{10^9}")
            st.latex(
                rf"\text{{Gb/sample}} = \dfrac{{{format_region_size(int(output_bp * eff_fraction))}/{samples}}}{{10^9}}"
                rf" = \mathbf{{{usable_gb_per_sample:.2f}}}\ \text{{Gb}}"
            )
            if variable == "Genome size":
                st.caption(
                    "Genome-size solving is not meaningful for shotgun metagenomics; "
                    "the calculator reports usable data volume per sample instead."
                )


def render_run_planning_math_explainer(
    *,
    plan: RunPlan,
    singular_unit: str,
    plural_unit: str,
) -> None:
    """Math explainer for converting theoretical capacity into integer units."""

    st.divider()
    with st.expander("How run planning is calculated", expanded=False):
        st.markdown("#### Operational loading model")
        st.latex(r"C = \text{theoretical samples per sequencing unit}")
        st.latex(r"M = \text{reserve margin (\%)}")
        st.latex(r"N = \text{samples to plan}")
        st.latex(r"C_{adj} = C \times \left(1 - \frac{M}{100}\right)")
        st.latex(r"C_{rec} = \left\lfloor C_{adj}\right\rfloor")
        st.latex(r"U = \left\lceil \frac{N}{C_{rec}}\right\rceil")

        st.markdown("#### Values")
        st.latex(
            rf"C_{{adj}} = {plan.theoretical_samples_per_unit:.2f}"
            rf"\times \left(1 - \frac{{{plan.reserve_margin_pct:.1f}}}{{100}}\right)"
            rf" = \mathbf{{{plan.adjusted_samples_per_unit:.2f}}}"
        )

        if plan.recommended_samples_per_unit > 0:
            st.latex(
                rf"C_{{rec}} = \left\lfloor {plan.adjusted_samples_per_unit:.2f} \right\rfloor"
                rf" = \mathbf{{{plan.recommended_samples_per_unit}}}"
            )
            st.latex(
                rf"U = \left\lceil \frac{{{plan.planning_samples}}}{{{plan.recommended_samples_per_unit}}} \right\rceil"
                rf" = \mathbf{{{plan.units_required}}}\ \text{{{plural_unit}}}"
            )
            st.latex(
                rf"\text{{unused capacity}} = ({plan.units_required}\times {plan.recommended_samples_per_unit})"
                rf" - {plan.planning_samples} = \mathbf{{{plan.unused_capacity_samples:.1f}}}\ \text{{samples}}"
            )
        else:
            st.latex(
                rf"U = \left\lceil \frac{{{plan.planning_samples}}}{{{plan.adjusted_samples_per_unit:.2f}}} \right\rceil"
                rf" = \mathbf{{{plan.units_required}}}\ \text{{{plural_unit}}}"
            )
            st.caption(
                f"Less than one whole sample fits per {singular_unit} after the reserve "
                "margin, so required units are calculated from fractional adjusted capacity."
            )
