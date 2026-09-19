"""
Lifecycle Carbon Footprint Comparison of Electricity Generation Technologies

Compares full lifecycle GHG emissions (gCO2eq/kWh) across 7 power generation
technologies using IPCC AR6 WGIII median values and China-specific grid data.

Framework: GHG Protocol Lifecycle Assessment (Scope 1 + Scope 3 upstream/downstream)
Data sources:
  - IPCC AR6 WGIII Annex III (Technology-specific cost and performance parameters)
  - China Electricity Council annual statistics
  - MEE China Regional Grid Emission Factors (2023)
"""

import pandas as pd
import numpy as np

# =============================================================================
# IPCC AR6 WGIII Lifecycle Emission Factors (gCO2eq/kWh)
# Table: median values from Annex III, Technology-specific parameters
# =============================================================================

LIFECYCLE_FACTORS = {
    "Coal": {
        "technology": "Subcritical/Supercritical Pulverized Coal",
        "construction": 1.0,
        "fuel_supply": 27.0,      # mining, transport
        "operation": 820.0,       # combustion
        "decommission": 1.0,
        "total_median": 820.0,
        "range_low": 740.0,
        "range_high": 910.0,
    },
    "Natural Gas (CCGT)": {
        "technology": "Combined Cycle Gas Turbine",
        "construction": 1.0,
        "fuel_supply": 67.0,      # extraction, processing, LNG
        "operation": 410.0,
        "decommission": 0.5,
        "total_median": 490.0,
        "range_low": 410.0,
        "range_high": 650.0,
    },
    "Solar PV (Utility)": {
        "technology": "Crystalline Silicon, Utility-Scale",
        "construction": 33.0,     # module manufacturing, BOS
        "fuel_supply": 0.0,
        "operation": 3.0,         # maintenance
        "decommission": 5.0,
        "total_median": 41.0,
        "range_low": 18.0,
        "range_high": 73.0,
    },
    "Wind Onshore": {
        "technology": "Onshore Wind Turbine",
        "construction": 7.0,
        "fuel_supply": 0.0,
        "operation": 3.0,
        "decommission": 1.0,
        "total_median": 11.0,
        "range_low": 7.0,
        "range_high": 56.0,
    },
    "Wind Offshore": {
        "technology": "Offshore Wind Turbine",
        "construction": 8.0,
        "fuel_supply": 0.0,
        "operation": 4.0,
        "decommission": 1.0,
        "total_median": 12.0,
        "range_low": 8.0,
        "range_high": 35.0,
    },
    "Nuclear": {
        "technology": "Gen III Light Water Reactor",
        "construction": 1.0,
        "fuel_supply": 8.0,       # mining, enrichment
        "operation": 0.0,
        "decommission": 3.0,
        "total_median": 12.0,
        "range_low": 5.0,
        "range_high": 22.0,
    },
    "Hydropower": {
        "technology": "Reservoir Hydropower",
        "construction": 17.0,
        "fuel_supply": 0.0,
        "operation": 3.0,         # reservoir emissions (biogenic CH4)
        "decommission": 4.0,
        "total_median": 24.0,
        "range_low": 6.0,
        "range_high": 147.0,
    },
}

# =============================================================================
# China Grid Mix Evolution (% share by technology)
# Source: China Electricity Council / National Energy Administration
# =============================================================================

CHINA_GRID_MIX = {
    2015: {"Coal": 70.4, "Natural Gas (CCGT)": 3.0, "Hydropower": 19.4,
           "Wind Onshore": 3.2, "Wind Offshore": 0.1, "Solar PV (Utility)": 0.9, "Nuclear": 3.0},
    2016: {"Coal": 68.1, "Natural Gas (CCGT)": 3.2, "Hydropower": 19.4,
           "Wind Onshore": 3.9, "Wind Offshore": 0.1, "Solar PV (Utility)": 1.2, "Nuclear": 3.5},
    2017: {"Coal": 66.5, "Natural Gas (CCGT)": 3.3, "Hydropower": 18.6,
           "Wind Onshore": 4.7, "Wind Offshore": 0.2, "Solar PV (Utility)": 1.8, "Nuclear": 3.9},
    2018: {"Coal": 64.9, "Natural Gas (CCGT)": 3.4, "Hydropower": 17.6,
           "Wind Onshore": 5.1, "Wind Offshore": 0.2, "Solar PV (Utility)": 2.5, "Nuclear": 4.2},
    2019: {"Coal": 63.0, "Natural Gas (CCGT)": 3.5, "Hydropower": 17.8,
           "Wind Onshore": 5.4, "Wind Offshore": 0.3, "Solar PV (Utility)": 3.0, "Nuclear": 4.8},
    2020: {"Coal": 61.7, "Natural Gas (CCGT)": 3.6, "Hydropower": 17.8,
           "Wind Onshore": 5.6, "Wind Offshore": 0.4, "Solar PV (Utility)": 3.4, "Nuclear": 4.9},
    2021: {"Coal": 60.1, "Natural Gas (CCGT)": 3.7, "Hydropower": 16.0,
           "Wind Onshore": 6.4, "Wind Offshore": 0.7, "Solar PV (Utility)": 3.9, "Nuclear": 5.0},
    2022: {"Coal": 58.4, "Natural Gas (CCGT)": 3.6, "Hydropower": 15.3,
           "Wind Onshore": 7.2, "Wind Offshore": 1.0, "Solar PV (Utility)": 4.8, "Nuclear": 5.0},
    2023: {"Coal": 56.2, "Natural Gas (CCGT)": 3.5, "Hydropower": 14.8,
           "Wind Onshore": 7.8, "Wind Offshore": 1.3, "Solar PV (Utility)": 6.2, "Nuclear": 5.0},
    2024: {"Coal": 53.5, "Natural Gas (CCGT)": 3.4, "Hydropower": 14.5,
           "Wind Onshore": 8.2, "Wind Offshore": 1.7, "Solar PV (Utility)": 8.5, "Nuclear": 5.2},
}

# =============================================================================
# Regional Grid Emission Factors (tCO2/MWh) — MEE 2023
# =============================================================================

REGIONAL_GRID_EF = {
    "华北区域电网": 0.8843,
    "东北区域电网": 0.8019,
    "华东区域电网": 0.7035,
    "华中区域电网": 0.5257,
    "西北区域电网": 0.8922,
    "南方区域电网": 0.5271,  # GBA is here
    "全国平均": 0.5810,
}


def build_lca_dataframe():
    """Build a DataFrame with all lifecycle emission data."""
    records = []
    for tech, data in LIFECYCLE_FACTORS.items():
        records.append({
            "technology": tech,
            "description": data["technology"],
            "construction": data["construction"],
            "fuel_supply": data["fuel_supply"],
            "operation": data["operation"],
            "decommission": data["decommission"],
            "total_median": data["total_median"],
            "range_low": data["range_low"],
            "range_high": data["range_high"],
        })
    return pd.DataFrame(records)


def calculate_grid_intensity(year):
    """Calculate weighted-average grid emission intensity for a given year."""
    mix = CHINA_GRID_MIX.get(year)
    if not mix:
        return None
    total = 0
    for tech, share in mix.items():
        ef = LIFECYCLE_FACTORS[tech]["total_median"]
        total += (share / 100) * ef
    return round(total, 1)


def calculate_grid_intensity_series():
    """Calculate grid intensity for all years."""
    records = []
    for year in sorted(CHINA_GRID_MIX.keys()):
        intensity = calculate_grid_intensity(year)
        coal_share = CHINA_GRID_MIX[year]["Coal"]
        renewable_share = sum(v for k, v in CHINA_GRID_MIX[year].items()
                             if k not in ["Coal", "Natural Gas (CCGT)", "Nuclear"])
        records.append({
            "year": year,
            "grid_intensity_gCO2eq_kWh": intensity,
            "coal_share_pct": coal_share,
            "renewable_share_pct": round(renewable_share, 1),
        })
    return pd.DataFrame(records)


def calculate_avoided_emissions(capacity_mw, tech, capacity_factor, grid_ef_gCO2_kWh, years=25):
    """
    Calculate lifetime avoided emissions from deploying renewable capacity.

    Args:
        capacity_mw: Installed capacity in MW
        tech: Technology name (must be in LIFECYCLE_FACTORS)
        capacity_factor: Annual capacity factor (0-1)
        grid_ef_gCO2_kWh: Grid emission factor being displaced (gCO2eq/kWh)
        years: Project lifetime
    Returns:
        dict with generation, gross/net avoided emissions
    """
    annual_gen_mwh = capacity_mw * capacity_factor * 8760
    annual_gen_gwh = annual_gen_mwh / 1000

    tech_ef = LIFECYCLE_FACTORS[tech]["total_median"]
    gross_avoided_tCO2_yr = annual_gen_mwh * grid_ef_gCO2_kWh / 1e6
    net_avoided_tCO2_yr = annual_gen_mwh * (grid_ef_gCO2_kWh - tech_ef) / 1e6

    return {
        "technology": tech,
        "capacity_mw": capacity_mw,
        "capacity_factor": capacity_factor,
        "annual_generation_gwh": round(annual_gen_gwh, 1),
        "tech_lifecycle_ef": tech_ef,
        "displaced_grid_ef": grid_ef_gCO2_kWh,
        "gross_avoided_tCO2_per_year": round(gross_avoided_tCO2_yr, 0),
        "net_avoided_tCO2_per_year": round(net_avoided_tCO2_yr, 0),
        "lifetime_years": years,
        "lifetime_net_avoided_tCO2": round(net_avoided_tCO2_yr * years, 0),
    }


def scenario_china_2030():
    """
    Scenario: China's 2030 NDC target grid mix projection.
    Non-fossil share >= 25% of primary energy (~40-45% of electricity).
    """
    projected_2030 = {
        "Coal": 45.0,
        "Natural Gas (CCGT)": 4.0,
        "Hydropower": 14.0,
        "Wind Onshore": 10.0,
        "Wind Offshore": 3.0,
        "Solar PV (Utility)": 14.0,
        "Nuclear": 6.5,
    }
    # Normalize
    total = sum(projected_2030.values())
    projected_2030 = {k: round(v / total * 100, 1) for k, v in projected_2030.items()}

    intensity = sum(
        (share / 100) * LIFECYCLE_FACTORS[tech]["total_median"]
        for tech, share in projected_2030.items()
    )
    return projected_2030, round(intensity, 1)


if __name__ == "__main__":
    # Summary output
    lca_df = build_lca_dataframe()
    print("Lifecycle Emission Factors (gCO2eq/kWh)")
    print("=" * 70)
    print(lca_df[["technology", "total_median", "range_low", "range_high",
                   "construction", "fuel_supply", "operation"]].to_string(index=False))

    print("\n\nChina Grid Emission Intensity Trend")
    print("=" * 50)
    grid_df = calculate_grid_intensity_series()
    print(grid_df.to_string(index=False))

    print("\n\nAvoided Emissions Example: 100MW Solar PV in South China Grid")
    print("=" * 60)
    result = calculate_avoided_emissions(
        capacity_mw=100,
        tech="Solar PV (Utility)",
        capacity_factor=0.16,
        grid_ef_gCO2_kWh=REGIONAL_GRID_EF["南方区域电网"] * 1000,
    )
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Save data
    lca_df.to_csv("../data/lifecycle_emission_factors.csv", index=False)
    grid_df.to_csv("../data/china_grid_intensity.csv", index=False)
    print("\nData saved to ../data/")
