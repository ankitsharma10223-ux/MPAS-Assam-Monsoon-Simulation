# MPAS-Atmosphere Regional Monsoon Simulation: Assam, India

Numerical simulation and evaluation of the 15–19 July 2026 extreme monsoon rainfall episode over the Assam Brahmaputra Valley using **MPAS-Atmosphere v8.4.2** on a regional Voronoi mesh (~15 km resolution, 7,829 cells).

## 📊 Episode Evaluation against IMD 0.25° Observations

| Verification Date | IMD Observed (Assam) | MPAS Baseline (Tiedtke) | MPAS Exp 1 (Grell-Freitas) |
| :--- | :---: | :---: | :---: |
| **15 July 2026** | 9.1 mm | 27.4 mm | 25.5 mm |
| **16 July 2026** | 21.4 mm | 14.2 mm | **17.3 mm** *(Improved)* |
| **17 July 2026** | 12.7 mm | 6.3 mm | **9.1 mm** *(Improved)* |
| **18 July 2026** | 8.6 mm | 13.4 mm | 18.7 mm |
| **19 July 2026** | 28.0 mm | 20.8 mm | 38.6 mm |
| **5-Day Total** | **79.8 mm** | **82.1 mm (+2.8%)** | **109.2 mm (+36.8%)** |

## 🎬 Rainfall Animation & Visualizations
- `fig_mpas_assam_rainfall_clean.png`: 6-panel daily evolution across Assam.
- `mpas_assam_monsoon_movie.gif`: Broadcast-grade animated movie with embedded colorbar.
- `fig_mpas_assam_imd_official.png`: IMD standard publication format clipped strictly to Assam.

## 🚀 Repository Contents
- `namelist.atmosphere.tiedtke_baseline`: Baseline physics configuration (`cu_tiedtke` + `mp_wsm6`).
- `namelist.atmosphere.grell_freitas`: Scale-aware sensitivity configuration (`cu_grell_freitas` + `mp_wsm6`).
- `streams.atmosphere`: MPAS stream I/O specifications.
- `extract_mpas_rainfall.py`: Extracts 24-hr IMD daily rainfall accumulations (03Z–03Z).
- `interpolate_to_imd_grid.py`: Remaps Voronoi mesh cells to the IMD 0.25° grid.
- `plot_clean_white_assam.py`: Generates the figures and animated movie.
