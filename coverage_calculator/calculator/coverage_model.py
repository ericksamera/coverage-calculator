# coverage_calculator/calculator/coverage_model.py

class CoverageCalculator:
    def __init__(self, *, region_size_bp: int, depth: float, samples: int,
                 output_bp: float, duplication_pct: float, on_target_pct: float):
        self.region_size_bp = region_size_bp
        self.depth = depth
        self.samples = samples
        self.output_bp = output_bp
        self.duplication_pct = duplication_pct
        self.on_target_pct = on_target_pct

    def _effective_yield_fraction(self) -> float:
        """
        Returns the fraction of usable reads after duplication and on-target filtering.
        """
        return (1 - self.duplication_pct / 100.0) * (self.on_target_pct / 100.0)

    def calc_samples_per_flow_cell(self) -> float:
        """
        Returns number of samples supported per flow cell.
        """
        total_required = self.region_size_bp * self.depth / self._effective_yield_fraction()
        return self.output_bp / total_required

    def calc_depth(self) -> float:
        """
        Returns achievable depth for given number of samples.
        """
        per_sample_output = self.output_bp / self.samples
        return per_sample_output * self._effective_yield_fraction() / self.region_size_bp

    def calc_genome_size(self) -> float:
        """
        Returns the maximum genome size (in bp) that can be covered at the specified depth.
        """
        usable_per_sample = (self.output_bp / self.samples) * self._effective_yield_fraction()
        return usable_per_sample / self.depth
