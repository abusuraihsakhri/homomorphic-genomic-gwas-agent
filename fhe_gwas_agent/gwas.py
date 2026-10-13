"""Plaintext 2x2 allelic association test (not homomorphic encryption).

This unadjusted Pearson test is illustrative and is not a substitute for
individual-level, covariate-adjusted GWAS or ancestry/population QC.
"""
from dataclasses import dataclass, asdict
from math import erfc, isfinite, sqrt
from typing import Optional


@dataclass(frozen=True)
class AllelicAssociationResult:
    chi_square: float
    p_value: float
    odds_ratio: Optional[float]
    expected_counts: tuple
    sparse_expected_counts: bool
    case_alt_frequency: float
    control_alt_frequency: float

    def to_dict(self) -> dict:
        return asdict(self)


def allelic_chi_square(case_alt: int, case_ref: int,
                       control_alt: int, control_ref: int) -> AllelicAssociationResult:
    """Pearson chi-square with 1 df for a 2x2 *allele* count table.

    All four inputs must be non-negative integer allele counts. Each row and
    column must have a positive total. This function does not encrypt data,
    implement logistic regression, or correct for GWAS confounding.
    """
    values = (case_alt, case_ref, control_alt, control_ref)
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError("Allele counts must be non-negative integers")
    a, b, c, d = values
    r1, r2, c1, c2 = a + b, c + d, a + c, b + d
    if not all((r1, r2, c1, c2)):
        raise ValueError("Both phenotype groups and both alleles need positive totals")
    n = r1 + r2
    if n > 10_000_000:
        raise ValueError("Total allele count exceeds supported precision limit (10 million)")
    expected = (r1*c1/n, r1*c2/n, r2*c1/n, r2*c2/n)
    chi2 = n * (a*d - b*c)**2 / (r1*r2*c1*c2)
    p = erfc(sqrt(chi2 / 2))
    if not isfinite(chi2):
        raise ValueError("Counts are too large for a finite floating-point statistic")
    odds = a*d/(b*c) if b*c else None
    return AllelicAssociationResult(
        chi_square=chi2, p_value=p, odds_ratio=odds,
        expected_counts=expected,
        sparse_expected_counts=any(x < 5 for x in expected),
        case_alt_frequency=a/r1, control_alt_frequency=c/r2,
    )
