"""Reference and edge-case tests for the separate plaintext GWAS demonstration."""
import pytest
from fhe_gwas_agent.gwas import allelic_chi_square


def test_known_allelic_table():
    result = allelic_chi_square(30, 70, 15, 85)
    assert result.chi_square == pytest.approx(6.451612903225806)
    assert result.p_value == pytest.approx(0.011085166380602699)
    assert result.odds_ratio == pytest.approx(30*85/(70*15))
    assert result.case_alt_frequency == 0.3
    assert result.control_alt_frequency == 0.15
    assert not result.sparse_expected_counts


def test_equal_frequencies():
    result = allelic_chi_square(25, 75, 50, 150)
    assert result.chi_square == 0
    assert result.p_value == 1
    assert result.odds_ratio == 1


def test_sparse_and_zero_cell():
    result = allelic_chi_square(2, 8, 0, 10)
    assert result.sparse_expected_counts
    assert result.odds_ratio is None
    assert 0 <= result.p_value <= 1


@pytest.mark.parametrize('values', [(-1, 5, 2, 3), (True, 5, 2, 3),
    (1.0, 5, 2, 3), (0, 0, 1, 3), (0, 4, 0, 6), (3, 0, 2, 0)])
def test_invalid_tables(values):
    with pytest.raises(ValueError):
        allelic_chi_square(*values)


def test_allele_label_swap_preserves_significance():
    x = allelic_chi_square(10, 90, 25, 75)
    y = allelic_chi_square(90, 10, 75, 25)
    assert x.chi_square == pytest.approx(y.chi_square)
    assert x.p_value == pytest.approx(y.p_value)
    assert x.odds_ratio*y.odds_ratio == pytest.approx(1)


def test_unrealistically_large_counts():
    with pytest.raises(ValueError, match="precision limit"):
        allelic_chi_square(10**15, 100, 20, 80)
