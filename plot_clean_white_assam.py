#!/usr/bin/env python3
"""
Clean White Theme: MPAS-Atmosphere Assam Rainfall Visualizations & Video
- Light / White background
- Colorbar included directly in the video
- Slower, graceful animation speed
- Pure NetCDF4, NumPy, Matplotlib (zero Scipy / Shapely dependencies)
"""
import os
import json
import urllib.request
import subprocess
import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Polygon as MplPolygon, PathPatch
from matplotlib.path import Path

def download_file(url, target_path):
    if not os.path.exists(target_path) or os.path.getsize(target_path) < 1000:
        print(f"Downloading {os.path.basename(target_path)}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response, open(target_path, 'wb') as out_file:
            out_file.write(response.read())

def parse_geojson_polygons(geojson_path, filter_keys=None):
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    results = []
    for feat in data.get('features', []):
        props = feat.get('properties', {})
        name = props.get('NAME_1') or props.get('ST_NM') or props.get('ADMIN') or props.get('name') or ''
        if filter_keys is not None and name not in filter_keys:
            continue
        geom = feat.get('geometry', {})
        gtype = geom.get('type')
        coords = geom.get('coordinates', [])
        rings = []
        if gtype == 'Polygon':
            for r in coords: rings.append(np.array(r))
        elif gtype == 'MultiPolygon':
            for poly in coords:
                for r in poly: rings.append(np.array(r))
        if rings:
            results.append((name, rings))
    return results

def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def smooth_interp_numpy(grid, fine_factor=8):
    ny, nx = grid.shape
    y_old = np.linspace(0, 1, ny)
    x_old = np.linspace(0, 1, nx)
    y_new = np.linspace(0, 1, ny * fine_factor)
    x_new = np.linspace(0, 1, nx * fine_factor)

    temp = np.zeros((ny, nx * fine_factor))
    for i in range(ny):
        temp[i, :] = np.interp(x_new, x_old, grid[i, :])
    out = np.zeros((ny * fine_factor, nx * fine_factor))
    for j in range(nx * fine_factor):
        out[:, j] = np.interp(y_new, y_old, temp[:, j])

    k = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=float) / 16.0
    p = np.pad(out, 1, mode='edge')
    sm = (k[0,0]*p[:-2,:-2] + k[0,1]*p[:-2,1:-1] + k[0,2]*p[:-2,2:] +
          k[1,0]*p[1:-1,:-2] + k[1,1]*p[1:-1,1:-1] + k[1,2]*p[1:-1,2:] +
          k[2,0]*p[2:,:-2] + k[2,1]*p[2:,1:-1] + k[2,2]*p[2:,2:])
    return np.clip(sm, 0, None)

def main():
    print("=" * 65)
    print("Clean White Theme Visualization Engine")
    print("=" * 65)

    nc_file = "mpas_rainfall_imd0p25.nc"
    if not os.path.exists(nc_file):
        print(f"Error: {nc_file} not found. Running extraction first...")
        os.system("/home/ankit/SAM_mpas/miniconda3/bin/python extract_mpas_rainfall.py")
        os.system("/home/ankit/SAM_mpas/miniconda3/bin/python interpolate_to_imd_grid.py")

    download_file("https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson", "india_states.geojson")
    download_file("https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson", "countries.geojson")

    ds = nc.Dataset(nc_file, 'r')
    lats = np.array(ds.variables['lat'][:])
    lons = np.array(ds.variables['lon'][:])
    LON, LAT = np.meshgrid(lons, lats)

    ne_states = ['Assam', 'Arunachal Pradesh', 'Meghalaya', 'Nagaland', 'Manipur', 'Mizoram', 'Tripura', 'West Bengal']
    states_data = parse_geojson_polygons("india_states.geojson", ne_states)
    
    assam_rings = []
    other_state_rings = []
    for s_name, s_rings in states_data:
        if s_name == 'Assam':
            assam_rings.extend(s_rings)
        else:
            other_state_rings.extend(s_rings)

    neighbor_countries = ['Bangladesh', 'Bhutan', 'China', 'Myanmar']
    country_data = parse_geojson_polygons("countries.geojson", neighbor_countries)
    country_rings = []
    for c_name, c_rings in country_data:
        country_rings.extend(c_rings)

    mask_assam = np.zeros(LON.shape, dtype=bool)
    for i in range(len(lats)):
        for j in range(len(lons)):
            px, py = lons[j], lats[i]
            for ring in assam_rings:
                if point_in_poly(px, py, ring):
                    mask_assam[i, j] = True
                    break

    day_titles = [
        ('15 July 2026', 'rain_15_Jul', '24-hr IMD (03Z–03Z)'),
        ('16 July 2026', 'rain_16_Jul', '24-hr IMD (03Z–03Z)'),
        ('17 July 2026', 'rain_17_Jul', '24-hr IMD (03Z–03Z)'),
        ('18 July 2026', 'rain_18_Jul', '24-hr IMD (03Z–03Z)'),
        ('19 July 2026', 'rain_19_Jul', '24-hr IMD (03Z–03Z)'),
        ('15–19 July Total', 'rain_5day_total', '5-Day Total Rain')
    ]

    imd_obs_means = {
        'rain_15_Jul': 9.1,
        'rain_16_Jul': 21.4,
        'rain_17_Jul': 12.7,
        'rain_18_Jul': 8.6,
        'rain_19_Jul': 28.0,
        'rain_5day_total': 79.8
    }

    fine_res = 8
    fine_lats = np.linspace(lats.min(), lats.max(), len(lats) * fine_res)
    fine_lons = np.linspace(lons.min(), lons.max(), len(lons) * fine_res)
    FINE_LON, FINE_LAT = np.meshgrid(fine_lons, fine_lats)

    river_lons = [95.4, 94.8, 93.8, 93.0, 92.2, 91.6, 90.8, 90.1, 89.8]
    river_lats = [27.9, 27.4, 26.9, 26.6, 26.3, 26.1, 26.2, 26.0, 25.4]
    extent = [89.5, 96.5, 23.5, 28.5]

    # Precipitation Colormap
    gpm_colors = [
        "#cbe8f8", "#38bdf8", "#0284c7", "#10b981", 
        "#84cc16", "#facc15", "#fb923c", "#ef4444", "#a855f7", "#ec4899"
    ]
    gpm_levels = [1.0, 5.0, 10.0, 20.0, 35.0, 55.0, 80.0, 115.0, 160.0, 220.0]
    gpm_cmap = ListedColormap(gpm_colors)
    gpm_norm = BoundaryNorm(gpm_levels, gpm_cmap.N, extend='max')

    # -------------------------------------------------------------
    # 1. STATIC 6-PANEL FIGURE (WHITE BACKGROUND)
    # -------------------------------------------------------------
    print("Generating Clean White 6-Panel Figure...")
    fig = plt.figure(figsize=(22, 13), facecolor="#ffffff")
    plt.subplots_adjust(left=0.04, right=0.92, top=0.90, bottom=0.06, wspace=0.14, hspace=0.22)

    fig.text(0.04, 0.955, "MPAS-ATMOSPHERE (15 km) — ASSAM MONSOON RAINFALL SIMULATION",
             color="#0f172a", fontsize=18, weight="bold")
    fig.text(0.04, 0.932, "Regional 15 km Mesh (7,829 Cells) | Remapped to IMD 0.25° Grid | 15–19 July 2026",
             color="#475569", fontsize=12)
    fig.text(0.72, 0.945, "PHYSICS: Grell-Freitas (cu_grell_freitas) + WSM6", color="#0369a1", fontsize=11, weight="bold")

    for idx, (title, varname, subtitle) in enumerate(day_titles):
        ax = fig.add_subplot(2, 3, idx + 1, facecolor="#f8fafc")
        raw_data = np.array(ds.variables[varname][:])
        smooth_data = smooth_interp_numpy(raw_data, fine_res)

        val_assam = raw_data[mask_assam]
        mean_assam = val_assam.mean()
        max_assam = val_assam.max()
        imd_mean = imd_obs_means[varname]

        # Land polygons (Clean light base)
        for r in country_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="#f1f5f9", edgecolor="#94a3b8", linewidth=0.8, zorder=1))
        for r in other_state_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=0.6, zorder=2))
        for r in assam_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="#ffffff", edgecolor="#0f172a", linewidth=1.8, zorder=3))

        # Rain Contours
        cf = ax.contourf(FINE_LON, FINE_LAT, smooth_data, levels=gpm_levels,
                         cmap=gpm_cmap, norm=gpm_norm, alpha=0.82, extend='max', zorder=4)

        # Re-draw clean borders on top
        for r in assam_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#0f172a", linewidth=1.8, zorder=5))
        for r in other_state_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#64748b", linewidth=0.6, linestyle=":", zorder=5))
        for r in country_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#334155", linewidth=0.9, zorder=5))

        # River & Cities
        ax.plot(river_lons, river_lats, color="#0284c7", linewidth=1.5, linestyle="--", zorder=6)
        ax.plot(91.73, 26.14, 'o', color="#0f172a", markersize=3.5, zorder=7)
        ax.text(91.85, 26.05, "Guwahati", color="#0f172a", fontsize=7.5, weight="bold", zorder=7)
        ax.plot(94.91, 27.47, 'o', color="#0f172a", markersize=3.5, zorder=7)
        ax.text(93.9, 27.55, "Dibrugarh", color="#0f172a", fontsize=7.5, weight="bold", zorder=7)

        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.tick_params(colors="#334155", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#cbd5e1")
        ax.grid(color="#e2e8f0", linestyle=":", linewidth=0.7)

        # Clean HUD Box
        hud_text = (
            f"{title}\n"
            f"Assam Mean: {mean_assam:.1f} mm | IMD Obs: {imd_mean:.1f} mm\n"
            f"Assam Peak: {max_assam:.1f} mm"
        )
        ax.text(0.03, 0.96, hud_text, transform=ax.transAxes,
                fontsize=8.5, verticalalignment='top', color="#0f172a",
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#ffffff', edgecolor='#0284c7', alpha=0.92, lw=1))

        ax.set_title(f"{title} ({subtitle})", color="#0f172a", fontsize=11, weight="bold", pad=7)
        if idx % 3 == 0: ax.set_ylabel("Latitude (°N)", color="#334155", fontsize=10)
        if idx >= 3: ax.set_xlabel("Longitude (°E)", color="#334155", fontsize=10)

    # Colorbar
    cbar_ax = fig.add_axes([0.935, 0.12, 0.016, 0.73])
    cb = fig.colorbar(cf, cax=cbar_ax, orientation="vertical", extend='max')
    cb.set_label("Rainfall Rate (mm / day)", color="#0f172a", fontsize=11, weight="bold", labelpad=10)
    cb.ax.yaxis.set_tick_params(color="#334155", labelsize=9.5)
    cb.outline.set_edgecolor("#94a3b8")

    fig.savefig("fig_mpas_assam_rainfall_clean.png", dpi=250, facecolor='#ffffff')
    plt.close(fig)
    print("Saved: fig_mpas_assam_rainfall_clean.png")

    # -------------------------------------------------------------
    # 2. ANIMATED MOVIE (LIGHT THEME, SLOWER SPEED, COLORBAR INCLUDED)
    # -------------------------------------------------------------
    print("Generating Slower Animated Video with Embedded Colorbar...")
    days_data = [np.array(ds.variables[v][:]) for v in ['rain_15_Jul', 'rain_16_Jul', 'rain_17_Jul', 'rain_18_Jul', 'rain_19_Jul']]
    date_labels = ['15 July 2026', '16 July 2026', '17 July 2026', '18 July 2026', '19 July 2026']

    all_frames, all_lbls, all_stats, all_durations = [], [], [], []
    
    # Pause on each day for ~1.2 seconds, with gentle smooth transitions
    for d_idx in range(len(days_data)):
        d_curr_smooth = smooth_interp_numpy(days_data[d_idx], fine_res)
        val_a = days_data[d_idx][mask_assam]

        # Hold main day for 4 frames (each ~300ms = ~1.2 seconds hold)
        for _ in range(4):
            all_frames.append(d_curr_smooth)
            all_lbls.append(date_labels[d_idx])
            all_stats.append((val_a.mean(), val_a.max()))

        # Transitions to next day
        if d_idx < len(days_data) - 1:
            d_next = days_data[d_idx + 1]
            for alpha in np.linspace(0.25, 0.75, 3):
                interp = (1.0 - alpha) * days_data[d_idx] + alpha * d_next
                interp_smooth = smooth_interp_numpy(interp, fine_res)
                val_interp = interp[mask_assam]
                all_frames.append(interp_smooth)
                all_lbls.append(f"{date_labels[d_idx]} ➔ {date_labels[d_idx+1]}")
                all_stats.append((val_interp.mean(), val_interp.max()))

    ds.close()

    os.makedirs("movie_light_temp", exist_ok=True)
    fig_m = plt.figure(figsize=(11, 7), facecolor="#ffffff")
    ax_m = fig_m.add_axes([0.08, 0.09, 0.78, 0.77], facecolor="#f8fafc")
    cbar_ax_m = fig_m.add_axes([0.88, 0.10, 0.022, 0.75])
    from matplotlib.cm import ScalarMappable
    sm = ScalarMappable(norm=gpm_norm, cmap=gpm_cmap)
    sm.set_array([])
    cb_m = fig_m.colorbar(sm, cax=cbar_ax_m, orientation="vertical", extend='max')
    cb_m.set_label("Precipitation (mm / day)", color="#0f172a", fontsize=9.5, weight="bold")
    cb_m.ax.yaxis.set_tick_params(color="#334155", labelsize=8.5)
    cb_m.outline.set_edgecolor("#cbd5e1")
    img_files = []

    for f_idx, (f_data, f_lbl, (f_mean, f_max)) in enumerate(zip(all_frames, all_lbls, all_stats)):
        ax_m.clear()
        ax_m.set_facecolor("#f8fafc")

        for r in country_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="#f1f5f9", edgecolor="#94a3b8", linewidth=0.8, zorder=1))
        for r in other_state_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=0.6, zorder=2))
        for r in assam_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="#ffffff", edgecolor="#0f172a", linewidth=1.8, zorder=3))

        cf_m = ax_m.contourf(FINE_LON, FINE_LAT, f_data, levels=gpm_levels,
                            cmap=gpm_cmap, norm=gpm_norm, alpha=0.85, extend='max', zorder=4)

        for r in assam_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#0f172a", linewidth=1.8, zorder=5))
        for r in other_state_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#64748b", linewidth=0.6, linestyle=":", zorder=5))
        for r in country_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#334155", linewidth=0.9, zorder=5))

        ax_m.plot(river_lons, river_lats, color="#0284c7", linewidth=1.6, linestyle="--", zorder=6)
        ax_m.plot(91.73, 26.14, 'o', color="#0f172a", markersize=4, zorder=7)
        ax_m.text(91.85, 26.05, "Guwahati", color="#0f172a", fontsize=8.5, weight="bold", zorder=7)
        ax_m.plot(94.91, 27.47, 'o', color="#0f172a", markersize=4, zorder=7)
        ax_m.text(93.9, 27.55, "Dibrugarh", color="#0f172a", fontsize=8.5, weight="bold", zorder=7)

        ax_m.set_xlim(extent[0], extent[1])
        ax_m.set_ylim(extent[2], extent[3])
        ax_m.tick_params(colors="#334155", labelsize=9)
        for spine in ax_m.spines.values():
            spine.set_color("#cbd5e1")
        ax_m.grid(color="#e2e8f0", linestyle=":", linewidth=0.6)

        ax_m.set_xlabel("Longitude (°E)", color="#334155", fontsize=9.5)
        ax_m.set_ylabel("Latitude (°N)", color="#334155", fontsize=9.5)

        # Top Center Title (OUTSIDE the map)
        fig_m.text(0.47, 0.955, "MPAS-Atmosphere (15 km) — Assam Monsoon Rainfall Evolution",
                   color="#0f172a", fontsize=13, weight="bold", ha="center")

        # Top Center Timeline & Stats Banner (OUTSIDE the map, centered)
        timeline_banner = f"DATE: {f_lbl}   |   Assam State Mean: {f_mean:.1f} mm/day   |   Peak Cell: {f_max:.1f} mm/day"
        fig_m.text(0.47, 0.905, timeline_banner,
                   color="#0369a1", fontsize=9.5, weight="bold", ha="center",
                   bbox=dict(boxstyle="round,pad=0.4", facecolor="#f1f5f9", edgecolor="#0284c7", alpha=0.95, lw=1.2))

# Colorbar handled statically outside loop

        fpath = f"movie_light_temp/frame_{f_idx:03d}.png"
        fig_m.savefig(fpath, dpi=130, facecolor="#ffffff")
        img_files.append(fpath)

    plt.close(fig_m)

    out_gif = "mpas_assam_monsoon_movie.gif"
    try:
        from PIL import Image
        pil_frames = [Image.open(p) for p in img_files]
        # Duration: 350 ms per frame = smooth and relaxed speed
        pil_frames[0].save(out_gif, save_all=True, append_images=pil_frames[1:], duration=350, loop=0)
        print(f"Saved: {out_gif} via Pillow")
    except Exception:
        cmd = f"convert -delay 35 -loop 0 movie_light_temp/frame_*.png {out_gif}"
        subprocess.run(cmd, shell=True)
        print(f"Saved: {out_gif} via ImageMagick")

    print("=" * 65)
    print("ALL CLEAN LIGHT THEME VISUALIZATIONS COMPLETE!")
    print("=" * 65)

if __name__ == "__main__":
    main()
