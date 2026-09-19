"""Tests pinning the inputs to their sources and the arithmetic to its units.

Every test here corresponds to an error found in an earlier version of this
repository: factors attributed to the wrong IPCC report, a solar value taken
from the wrong row, generation shares that did not sum to 100%, regional factors
under the wrong labels, and avoided emissions a thousand times too small.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import lca_calculation as m  # noqa: E402


class TestAR5Transcription:
    """Values as printed in AR5 WGIII Annex III, Table A.III.2 (min / median / max)."""

    @pytest.mark.parametrize("technology,low,median,high", [
        ("Coal — PC", 740, 820, 910),
        ("Gas — Combined Cycle", 410, 490, 650),
        ("Solar PV — utility", 18, 48, 180),
        ("Solar PV — rooftop", 26, 41, 60),
        ("Wind onshore", 7.0, 11, 56),
        ("Wind offshore", 8.0, 12, 35),
        ("Nuclear", 3.7, 12, 110),
        ("Hydropower", 1.0, 24, 2200),
        ("Biomass — dedicated", 130, 230, 420),
    ])
    def test_lifecycle_values_match_the_table(self, technology, low, median, high):
        row = m.load_ar5().loc[technology]
        assert (row["lifecycle_min"], row["lifecycle_median"], row["lifecycle_max"]) == (low, median, high)

    def test_utility_solar_is_not_the_rooftop_value(self):
        # An earlier version used 41 — the rooftop median — for utility-scale PV.
        ar5 = m.load_ar5()
        assert ar5.loc["Solar PV — utility", "lifecycle_median"] == 48
        assert ar5.loc["Solar PV — rooftop", "lifecycle_median"] == 41

    def test_lifetimes_come_from_table_a_iii_1(self):
        ar5 = m.load_ar5()
        assert ar5.loc["Solar PV — utility", "plant_lifetime_yr"] == 25
        assert ar5.loc["Wind onshore", "plant_lifetime_yr"] == 25
        assert ar5.loc["Coal — PC", "plant_lifetime_yr"] == 40


class TestMix:
    def test_every_year_sums_to_100(self):
        mix = m.load_mix()
        shares = mix.drop(columns="generation_twh").sum(axis=1)
        assert ((shares - 100).abs() < 0.5).all()

    def test_every_category_is_either_mapped_or_named_as_uncovered(self):
        categories = set(m.load_mix().columns) - {"generation_twh"}
        assert categories == set(m.TECH_FOR_CATEGORY) | set(m.UNCOVERED)

    def test_intensity_is_over_the_covered_share_not_padded_with_zeros(self):
        # Half coal, half oil (no AR5 row): the covered half is all coal, so
        # the intensity is coal's, not half of it.
        shares = pd.Series({c: 0.0 for c in [*m.TECH_FOR_CATEGORY, *m.UNCOVERED]})
        shares["coal"], shares["oil"] = 50.0, 50.0
        intensity, covered = m.lifecycle_intensity(shares, m.load_ar5())
        assert covered == pytest.approx(50.0)
        assert intensity == pytest.approx(820.0)


class TestGridFactors:
    def test_south_and_north_are_the_official_2023_values(self):
        g = m.load_grid_factors()
        # An earlier version labelled 0.5271 as the South grid; it is Central's.
        assert g.loc["South", "kgco2_per_kwh"] == pytest.approx(0.4042)
        assert g.loc["Central", "kgco2_per_kwh"] == pytest.approx(0.5271)
        assert g.loc["North", "kgco2_per_kwh"] == pytest.approx(0.6361)


class TestAvoidedEmissions:
    def test_tonnes_are_tonnes(self):
        # 100 MW at 16% for a year is 140,160 MWh; at 404.2 g/kWh that is
        # 56,653 t — not the 57 t an earlier version reported.
        r = m.avoided_emissions(100, "Solar PV — utility", 0.16, 404.2)
        assert r["gross_avoided_t_per_year"] == pytest.approx(56_653, abs=2)

    def test_the_regional_ratio_does_not_depend_on_capacity_factor(self):
        ratios = []
        for cf in (0.12, 0.16, 0.25):
            s = m.avoided_emissions(100, "Solar PV — utility", cf, 404.2)["net_avoided_t_per_year"]
            n = m.avoided_emissions(100, "Solar PV — utility", cf, 636.1)["net_avoided_t_per_year"]
            ratios.append(n / s)
        assert max(ratios) - min(ratios) < 0.001


class TestPayback:
    def test_payback_is_lifecycle_times_lifetime_over_grid_factor(self):
        assert m.payback_years("Solar PV — utility", 404.2) == pytest.approx(48 * 25 / 404.2)

    def test_the_range_brackets_the_median(self):
        low = m.payback_years("Solar PV — utility", 404.2, "min")
        mid = m.payback_years("Solar PV — utility", 404.2, "median")
        high = m.payback_years("Solar PV — utility", 404.2, "max")
        assert low < mid < high
