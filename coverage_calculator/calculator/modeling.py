# coverage_calculator/calculator/modeling.py


def adjust_for_gc_bias(effective_bp: float, gc_dropout_factor: float = 0.05) -> float:
    """
    Reduce effective coverage by a factor to simulate GC/sequence bias.
    Example: 0.05 = 5% reduction in usable coverage.
    """
    return effective_bp * (1 - gc_dropout_factor)


def adjust_for_fragment_overlap(
    total_bases: float, read_length: int, fragment_size: int
) -> float:
    """
    Estimate the true usable base pairs based on fragment overlap.
    If reads overlap heavily (PE reads longer than fragments), subtract redundancy.
    """
    if fragment_size <= 0 or read_length <= 0:
        return total_bases

    # PE overlap estimation
    if 2 * read_length > fragment_size:
        redundancy_factor = (2 * read_length - fragment_size) / (2 * read_length)
        return total_bases * (1 - redundancy_factor)
    return total_bases
