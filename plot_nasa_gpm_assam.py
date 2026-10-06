#!/usr/bin/env python3
"""
NASA GPM / IMERG Broadcast Visualization & IMD Official Publication Pipeline
Self-contained: pure NetCDF4, NumPy, and Matplotlib. Zero Scipy required.
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
        print(f"Saved {target_path} ({os.path.getsize(target_path)/1024:.1f} KB)")

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
            for r in coords:
                rings.append(np.array(r))
        elif gtype == 'MultiPolygon':
            for poly in coords:
                for r in poly:
                    rings.append(np.array(r))
        if rings:
            results.append((name, rings))
    return results

def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def smooth_interp_numpy(grid, fine_factor=8):
    """Pure NumPy 2D bilinear interpolation + smoothing filter."""
    ny, nx = grid.shape
    y_old = np.linspace(0, 1, ny)
    x_old = np.linspace(0, 1, nx)
    y_new = np.linspace(0, 1, ny * fine_factor)
    x_new = np.linspace(0, 1, nx * fine_factor)

    # Separable bilinear interpolation
    temp = np.zeros((ny, nx * fine_factor))
    for i in range(ny):
        temp[i, :] = np.interp(x_new, x_old, grid[i, :])
    out = np.zeros((ny * fine_factor, nx * fine_factor))
    for j in range(nx * fine_factor):
        out[:, j] = np.interp(y_new, y_old, temp[:, j])

    # 3x3 smoothing filter
    k = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=float) / 16.0
    p = np.pad(out, 1, mode='edge')
    sm = (k[0,0]*p[:-2,:-2] + k[0,1]*p[:-2,1:-1] + k[0,2]*p[:-2,2:] +
          k[1,0]*p[1:-1,:-2] + k[1,1]*p[1:-1,1:-1] + k[1,2]*p[1:-1,2:] +
          k[2,0]*p[2:,:-2] + k[2,1]*p[2:,1:-1] + k[2,2]*p[2:,2:])
    return np.clip(sm, 0, None)

def main():
    print("=" * 65)
    print("NASA GPM / IMERG Broadcast Visualization Engine")
    print("=" * 65)

    nc_file = "mpas_rainfall_imd0p25.nc"
    if not os.path.exists(nc_file):
        print(f"Error: {nc_file} not found in current directory.")
        return

    # Download vector boundary files
    download_file("https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson", "india_states.geojson")
    download_file("https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson", "countries.geojson")

    ds = nc.Dataset(nc_file, 'r')
    lats = np.array(ds.variables['lat'][:])
    lons = np.array(ds.variables['lon'][:])
    LON, LAT = np.meshgrid(lons, lats)

    # Parse boundaries
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

    # Create Assam mask
    mask_assam = np.zeros(LON.shape, dtype=bool)
    for i in range(len(lats)):
        for j in range(len(lons)):
            px, py = lons[j], lats[i]
            for ring in assam_rings:
                if point_in_poly(px, py, ring):
                    mask_assam[i, j] = True
                    break
    print(f"Identified {np.sum(mask_assam)} grid points strictly inside Assam state.")

    day_titles = [
        ('15 July 2026', 'rain_15_Jul', '24-hr IMD Day (03Z-03Z)'),
        ('16 July 2026', 'rain_16_Jul', '24-hr IMD Day (03Z-03Z)'),
        ('17 July 2026', 'rain_17_Jul', '24-hr IMD Day (03Z-03Z)'),
        ('18 July 2026', 'rain_18_Jul', '24-hr IMD Day (03Z-03Z)'),
        ('19 July 2026', 'rain_19_Jul', '24-hr IMD Day (03Z-03Z)'),
        ('15-19 July Total', 'rain_5day_total', '5-Day Monsoon Cumulative')
    ]

    imd_obs_means = {
        'rain_15_Jul': 9.11,
        'rain_16_Jul': 21.43,
        'rain_17_Jul': 12.69,
        'rain_18_Jul': 8.59,
        'rain_19_Jul': 27.97,
        'rain_5day_total': 79.79
    }

    fine_res = 8
    fine_lats = np.linspace(lats.min(), lats.max(), len(lats) * fine_res)
    fine_lons = np.linspace(lons.min(), lons.max(), len(lons) * fine_res)
    FINE_LON, FINE_LAT = np.meshgrid(fine_lons, fine_lats)

    river_lons = [95.4, 94.8, 93.8, 93.0, 92.2, 91.6, 90.8, 90.1, 89.8]
    river_lats = [27.9, 27.4, 26.9, 26.6, 26.3, 26.1, 26.2, 26.0, 25.4]
    extent = [89.5, 96.5, 23.5, 28.5]

    # NASA GPM Color Palette
    gpm_colors = [
        "#0f2444", "#0284c7", "#06b6d4", "#10b981", 
        "#84cc16", "#eab308", "#f97316", "#ef4444", "#a855f7", "#f43f5e"
    ]
    gpm_levels = [1.0, 5.0, 10.0, 20.0, 35.0, 55.0, 80.0, 115.0, 160.0, 220.0]
    gpm_cmap = ListedColormap(gpm_colors)
    gpm_norm = BoundaryNorm(gpm_levels, gpm_cmap.N, extend='max')

    # -------------------------------------------------------------
    # FIGURE 1: NASA GPM BROADCAST MULTI-PANEL
    # -------------------------------------------------------------
    print("Generating Figure 1: NASA GPM Cinematic Broadcast...")
    fig = plt.figure(figsize=(22, 13), facecolor="#0b0f19")
    plt.subplots_adjust(left=0.04, right=0.92, top=0.90, bottom=0.06, wspace=0.14, hspace=0.22)

    fig.text(0.04, 0.955, "MPAS-ATMOSPHERE (15 km) — ASSAM MONSOON RAINFALL EPISODE",
             color="#ffffff", fontsize=20, weight="bold")
    fig.text(0.04, 0.932, "NASA GPM / IMERG Broadcast Standard | 15–19 July 2026 Simulation",
             color="#94a3b8", fontsize=13)
    fig.text(0.72, 0.955, "MODEL: MPAS-Atmosphere v8.4.2", color="#38bdf8", fontsize=11, weight="bold")
    fig.text(0.72, 0.935, "REGIONAL MESH: Assam 15 km (7,829 Cells)", color="#a5b4fc", fontsize=11)

    for idx, (title, varname, subtitle) in enumerate(day_titles):
        ax = fig.add_subplot(2, 3, idx + 1, facecolor="#0e1626")
        raw_data = np.array(ds.variables[varname][:])
        smooth_data = smooth_interp_numpy(raw_data, fine_res)

        val_assam = raw_data[mask_assam]
        mean_assam = val_assam.mean()
        max_assam = val_assam.max()
        imd_mean = imd_obs_means[varname]

        for r in country_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="#151d2f", edgecolor="#334155", linewidth=0.8, zorder=1))
        for r in other_state_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="#182338", edgecolor="#475569", linewidth=0.6, zorder=2))
        for r in assam_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="#1e2c47", edgecolor="#f59e0b", linewidth=1.8, zorder=3))

        cf = ax.contourf(FINE_LON, FINE_LAT, smooth_data, levels=gpm_levels,
                         cmap=gpm_cmap, norm=gpm_norm, alpha=0.85, extend='max', zorder=4)

        for r in assam_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#fbbf24", linewidth=1.6, zorder=5))
        for r in other_state_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#cbd5e1", linewidth=0.6, linestyle=":", zorder=5))
        for r in country_rings:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#e2e8f0", linewidth=0.9, zorder=5))

        ax.plot(river_lons, river_lats, color="#38bdf8", linewidth=1.5, linestyle="--", zorder=6)
        ax.plot(91.73, 26.14, 'o', color="#ffffff", markersize=3.5, zorder=7)
        ax.text(91.85, 26.05, "Guwahati", color="#f8fafc", fontsize=7.5, weight="bold", zorder=7)
        ax.plot(94.91, 27.47, 'o', color="#ffffff", markersize=3.5, zorder=7)
        ax.text(93.9, 27.55, "Dibrugarh", color="#f8fafc", fontsize=7.5, weight="bold", zorder=7)

        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.tick_params(colors="#94a3b8", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.grid(color="#334155", linestyle=":", linewidth=0.5, alpha=0.6)

        hud_text = (
            f"{title}\n"
            f"Assam Mean: {mean_assam:.1f} mm | IMD Obs: {imd_mean:.1f} mm\n"
            f"Assam Peak: {max_assam:.1f} mm"
        )
        ax.text(0.03, 0.96, hud_text, transform=ax.transAxes,
                fontsize=8.5, verticalalignment='top', color="#f8fafc",
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#090d16', edgecolor='#f59e0b', alpha=0.9, lw=1))

        ax.set_title(f"{title} ({subtitle})", color="#e2e8f0", fontsize=11, weight="bold", pad=7)
        if idx % 3 == 0:
            ax.set_ylabel("Latitude (°N)", color="#94a3b8", fontsize=10)
        if idx >= 3:
            ax.set_xlabel("Longitude (°E)", color="#94a3b8", fontsize=10)

    cbar_ax = fig.add_axes([0.935, 0.12, 0.016, 0.73])
    cb = fig.colorbar(cf, cax=cbar_ax, orientation="vertical", extend='max')
    cb.set_label("Precipitation Rate (mm / day)", color="#ffffff", fontsize=11, weight="bold", labelpad=10)
    cb.ax.yaxis.set_tick_params(color="#94a3b8", labelsize=9.5)
    plt.setp(plt.getp(cb.ax.axes, 'yticklabels'), color='#94a3b8')
    cb.outline.set_edgecolor("#475569")

    fig.savefig("fig_mpas_nasa_gpm_cinematic.png", dpi=250, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print("Saved: fig_mpas_nasa_gpm_cinematic.png")

    # -------------------------------------------------------------
    # FIGURE 2: IMD OFFICIAL PUBLICATION (CLIPPED TO ASSAM STATE)
    # -------------------------------------------------------------
    print("Generating Figure 2: IMD Official Publication Format...")
    imd_levels = [0.1, 2.5, 7.5, 15, 35, 65, 115, 200]
    imd_colors = ["#ffffff", "#b6e0f7", "#5cb3e8", "#0f52ba", "#2eb82e", "#ffd700", "#8b0000"]
    imd_cmap = ListedColormap(imd_colors)
    imd_cmap.set_over("#5c0000")
    imd_norm = BoundaryNorm(imd_levels, imd_cmap.N)

    verts, codes = [], []
    for ring in assam_rings:
        verts.extend(ring)
        codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 2) + [Path.CLOSEPOLY])
    clip_path = Path(verts, codes)

    fig2 = plt.figure(figsize=(20, 11), facecolor="#ffffff")
    plt.subplots_adjust(left=0.05, right=0.92, top=0.90, bottom=0.08, wspace=0.15, hspace=0.25)
    fig2.suptitle("MPAS-Atmosphere Regional Simulation: Daily Rainfall over Assam (IMD 03–03 UTC)\n"
                  "Standard IMD 0.25° Grid | Masked Strictly to Assam State Boundary",
                  fontsize=15, weight="bold", color="#0f172a", y=0.97)

    for idx, (title, varname, subtitle) in enumerate(day_titles):
        ax = fig2.add_subplot(2, 3, idx + 1)
        raw_data = np.array(ds.variables[varname][:])
        smooth_data = smooth_interp_numpy(raw_data, fine_res)

        for ring in assam_rings:
            ax.add_patch(MplPolygon(ring, closed=True, facecolor="#f8fafc", edgecolor="#0f172a", linewidth=1.2))

        cf2 = ax.contourf(FINE_LON, FINE_LAT, smooth_data, levels=imd_levels,
                          colors=imd_colors, extend='max', alpha=0.95)

        patch = PathPatch(clip_path, transform=ax.transData, facecolor='none', edgecolor='none')
        ax.add_patch(patch)
        try:
            cf2.set_clip_path(patch)
        except Exception:
            pass
        for c in getattr(cf2, "collections", []):
            c.set_clip_path(patch)

        for ring in assam_rings:
            ax.add_patch(MplPolygon(ring, closed=True, facecolor="none", edgecolor="#0f172a", linewidth=1.2, zorder=5))

        ax.plot(91.73, 26.14, 'o', color="#0f172a", markersize=3, zorder=6)
        ax.text(91.85, 26.05, "Guwahati", color="#0f172a", fontsize=7.5, weight="bold", zorder=6)
        ax.plot(94.91, 27.47, 'o', color="#0f172a", markersize=3, zorder=6)
        ax.text(93.9, 27.55, "Dibrugarh", color="#0f172a", fontsize=7.5, weight="bold", zorder=6)

        val_assam = raw_data[mask_assam]
        mean_assam = val_assam.mean()
        imd_mean = imd_obs_means[varname]
        bias_pct = ((mean_assam - imd_mean) / imd_mean) * 100

        ax.set_title(f"{title}\nMPAS: {mean_assam:.1f} mm | IMD Obs: {imd_mean:.1f} mm (Bias: {bias_pct:+.1f}%)",
                     fontsize=10.5, weight="bold", color="#1e293b", pad=6)
        ax.set_xlim(89.6, 96.2)
        ax.set_ylim(24.0, 28.2)
        ax.tick_params(labelsize=8.5)
        ax.grid(color="#cbd5e1", linestyle="--", linewidth=0.5, alpha=0.6)

        if idx % 3 == 0:
            ax.set_ylabel("Latitude (°N)", fontsize=9.5)
        if idx >= 3:
            ax.set_xlabel("Longitude (°E)", fontsize=9.5)

    cbar_ax2 = fig2.add_axes([0.935, 0.12, 0.016, 0.73])
    cb2 = fig2.colorbar(cf2, cax=cbar_ax2, orientation="vertical", extend='max')
    cb2.set_label("Daily Rainfall (mm / day) — IMD Categories", fontsize=11, weight="bold", labelpad=10)
    cb2.ax.tick_params(labelsize=9)

    fig2.savefig("fig_mpas_assam_imd_official.png", dpi=250, facecolor='white')
    plt.close(fig2)
    print("Saved: fig_mpas_assam_imd_official.png")

    # -------------------------------------------------------------
    # MOVIE: DYNAMIC ANIMATED BROADCAST GIF
    # -------------------------------------------------------------
    print("Generating Animated Movie Frames...")
    days_data = [np.array(ds.variables[v][:]) for v in ['rain_15_Jul', 'rain_16_Jul', 'rain_17_Jul', 'rain_18_Jul', 'rain_19_Jul']]
    date_labels = ['15 July 2026', '16 July 2026', '17 July 2026', '18 July 2026', '19 July 2026']

    all_frames, all_lbls, all_stats = [], [], []
    for d_idx in range(len(days_data) - 1):
        d_curr, d_next = days_data[d_idx], days_data[d_idx + 1]
        for alpha in np.linspace(0, 1, 5, endpoint=False):
            interp = (1.0 - alpha) * d_curr + alpha * d_next
            smooth = smooth_interp_numpy(interp, fine_res)
            all_frames.append(smooth)
            val_a = interp[mask_assam]
            all_lbls.append(f"{date_labels[d_idx]} ➔ {date_labels[d_idx+1]}")
            all_stats.append((val_a.mean(), val_a.max()))

    final_smooth = smooth_interp_numpy(days_data[-1], fine_res)
    for _ in range(5):
        all_frames.append(final_smooth)
        all_lbls.append(f"{date_labels[-1]} (Peak Episode)")
        all_stats.append((days_data[-1][mask_assam].mean(), days_data[-1][mask_assam].max()))

    ds.close()

    os.makedirs("movie_temp", exist_ok=True)
    fig_m, ax_m = plt.subplots(figsize=(11, 7), facecolor="#0b0f19")
    img_files = []

    for f_idx, (f_data, f_lbl, (f_mean, f_max)) in enumerate(zip(all_frames, all_lbls, all_stats)):
        ax_m.clear()
        ax_m.set_facecolor("#0e1626")
        for r in country_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="#151d2f", edgecolor="#334155", linewidth=0.8, zorder=1))
        for r in other_state_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="#182338", edgecolor="#475569", linewidth=0.6, zorder=2))
        for r in assam_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="#1e2c47", edgecolor="#f59e0b", linewidth=1.8, zorder=3))

        ax_m.contourf(FINE_LON, FINE_LAT, f_data, levels=gpm_levels,
                      cmap=gpm_cmap, norm=gpm_norm, alpha=0.85, extend='max', zorder=4)

        for r in assam_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#fbbf24", linewidth=1.8, zorder=5))
        for r in other_state_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#cbd5e1", linewidth=0.6, linestyle=":", zorder=5))
        for r in country_rings:
            ax_m.add_patch(MplPolygon(r, closed=True, facecolor="none", edgecolor="#e2e8f0", linewidth=0.9, zorder=5))

        ax_m.plot(river_lons, river_lats, color="#38bdf8", linewidth=1.6, linestyle="--", zorder=6)
        ax_m.plot(91.73, 26.14, 'o', color="#ffffff", markersize=4, zorder=7)
        ax_m.text(91.85, 26.05, "Guwahati", color="#f8fafc", fontsize=8.5, weight="bold", zorder=7)
        ax_m.plot(94.91, 27.47, 'o', color="#ffffff", markersize=4, zorder=7)
        ax_m.text(93.9, 27.55, "Dibrugarh", color="#f8fafc", fontsize=8.5, weight="bold", zorder=7)

        ax_m.set_xlim(extent[0], extent[1])
        ax_m.set_ylim(extent[2], extent[3])
        ax_m.tick_params(colors="#94a3b8", labelsize=9)
        for spine in ax_m.spines.values():
            spine.set_color("#334155")
        ax_m.grid(color="#334155", linestyle=":", linewidth=0.5, alpha=0.6)

        hud_box = (
            f"MISSION: MPAS-ATMOSPHERE (15 km) | ASSAM DOMAIN\n"
            f"DATE: {f_lbl}\n"
            f"ASSAM MEAN: {f_mean:.1f} mm/day | MAX: {f_max:.1f} mm/day"
        )
        ax_m.text(0.03, 0.95, hud_box, transform=ax_m.transAxes,
                  fontsize=9, verticalalignment='top', color="#f8fafc", weight="bold",
                  bbox=dict(boxstyle='round,pad=0.5', facecolor='#090d16', edgecolor='#f59e0b', alpha=0.9, lw=1.2))

        prog = (f_idx + 1) / len(all_frames)
        bx = np.linspace(89.7, 89.7 + prog * (96.3 - 89.7), 20)
        ax_m.plot(bx, [23.65] * len(bx), color="#f59e0b", linewidth=3.5, zorder=10)

        ax_m.set_title("NASA GPM / IMERG Broadcast Animation — Assam Monsoon Rainfall Evolution",
                       color="#ffffff", fontsize=11, weight="bold", pad=8)
        fpath = f"movie_temp/frame_{f_idx:03d}.png"
        fig_m.savefig(fpath, dpi=120, facecolor="#0b0f19")
        img_files.append(fpath)

    plt.close(fig_m)

    # Compile GIF: Try Pillow, else use system convert
    out_gif = "mpas_assam_gpm_movie.gif"
    try:
        from PIL import Image
        pil_frames = [Image.open(p) for p in img_files]
        pil_frames[0].save(out_gif, save_all=True, append_images=pil_frames[1:], duration=150, loop=0)
        print(f"Saved: {out_gif} via Pillow")
    except Exception:
        cmd = f"convert -delay 15 -loop 0 movie_temp/frame_*.png {out_gif}"
        subprocess.run(cmd, shell=True)
        print(f"Saved: {out_gif} via ImageMagick")

    print("=" * 65)
    print("ALL VISUALIZATIONS COMPLETE ON THE VM!")
    print("=" * 65)

if __name__ == "__main__":
    main()
