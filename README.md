# Lifecycle Carbon Footprint of Electricity Generation Technologies

Comparative lifecycle assessment (LCA) of greenhouse gas emissions across 7 electricity generation technologies, with application to China's grid decarbonisation and renewable deployment in the Greater Bay Area.

## Key Findings

- Coal emits **~820 gCO2eq/kWh** on a lifecycle basis — **75x more** than wind or nuclear
- China's grid emission intensity declined **~23%** from 2015 to 2024 as coal share dropped from 70% to 54%
- Renewable energy installations in the South China Grid (GBA) achieve **carbon payback within 1-2 years**
- The same 100MW solar deployment avoids **~60% more CO2** in North China (coal-heavy) than in South China
- Under China's 2030 NDC scenario, grid intensity could fall below **400 gCO2eq/kWh**

## Data Sources

- **IPCC AR6 WGIII Annex III**: Lifecycle emission factors (median, range) for all technologies
- **China Electricity Council**: Annual generation mix statistics
- **MEE (Ministry of Ecology and Environment)**: Regional grid emission factors (2023)

## Project Structure

```
Carbon-Footprint-LCA/
├── README.md
├── requirements.txt
├── data/
│   ├── lifecycle_emission_factors.csv
│   └── china_grid_intensity.csv
├── scripts/
│   └── lca_calculation.py
├── notebooks/
│   └── analysis.ipynb
└── outputs/
    ├── lifecycle_comparison.png
    ├── grid_decarbonisation.png
    ├── avoided_emissions.png
    ├── regional_grid_ef.png
    └── carbon_payback.png
```

## How to Run

```bash
pip install -r requirements.txt
cd scripts && python lca_calculation.py  # generate data
cd ../notebooks && jupyter notebook analysis.ipynb
```

## Technical Stack

- Python 3.10+
- pandas, numpy (data processing)
- matplotlib, seaborn (visualization)
- scipy (statistical analysis)
- jupyter (interactive analysis)

## License

MIT
