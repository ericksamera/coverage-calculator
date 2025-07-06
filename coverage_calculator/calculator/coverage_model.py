# coverage_calculator/calculator/coverage_model.py

class CoverageCalculator:
    def __init__(
            self,
            *,
            region_size_bp: int,
            depth: float,
            samples: int,
            output_bp: float,
            duplication_pct: float,
            on_target_pct: float
        ):
        if region_size_bp <= 0:
            raise ValueError("region_size_bp must be > 0")
        if depth <= 0:
            raise ValueError("depth must be > 0")
        if samples <= 0:
            raise ValueError("samples must be > 0")
        if output_bp < 0:
            raise ValueError("output_bp must be >= 0")
        if not (0 <= duplication_pct < 100):
            raise ValueError("duplication_pct must be in [0, 100)")
        if not (0 < on_target_pct <= 100):
            raise ValueError("on_target_pct must be in (0, 100]")

        self.region_size_bp = region_size_bp
        self.depth = depth
        self.samples = samples
        self.output_bp = output_bp
        self.duplication_pct = duplication_pct
        self.on_target_pct = on_target_pct

    def _effective_yield_fraction(self) -> float:
        """
        Returns the fraction of usable reads after duplication and on-target filtering.
        Returns 0.0 if inputs are invalid.
        """
        frac = (1 - self.duplication_pct / 100.0) * (self.on_target_pct / 100.0)
        return frac if frac > 0 else 0.0

    def calc_samples_per_flow_cell(self) -> float:
        """
        Returns number of samples supported per flow cell.
        Returns 0.0 if calculation is invalid (e.g. division by zero).
        """
        eff = self._effective_yield_fraction()
        if eff == 0:
            return 0.0
        total_required = self.region_size_bp * self.depth / eff
        if total_required == 0:
            return 0.0
        return self.output_bp / total_required

    def calc_depth(self) -> float:
        """
        Returns achievable depth for given number of samples.
        Returns 0.0 if calculation is invalid.
        """
        if self.samples == 0 or self.region_size_bp == 0:
            return 0.0
        eff = self._effective_yield_fraction()
        per_sample_output = self.output_bp / self.samples
        return per_sample_output * eff / self.region_size_bp

    def calc_genome_size(self) -> float:
        """
        Returns the maximum genome size (in bp) that can be covered at the specified depth.
        Returns 0.0 if calculation is invalid.
        """
        if self.samples == 0 or self.depth == 0:
            return 0.0
        eff = self._effective_yield_fraction()
        usable_per_sample = (self.output_bp / self.samples) * eff
        return usable_per_sample / self.depth

    def __repr__(self) -> str:
        return (f"CoverageCalculator(region_size_bp={self.region_size_bp}, depth={self.depth}, "
                f"samples={self.samples}, output_bp={self.output_bp}, "
                f"duplication_pct={self.duplication_pct}, on_target_pct={self.on_target_pct})")
