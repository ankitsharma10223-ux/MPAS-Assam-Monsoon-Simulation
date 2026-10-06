with open("plot_clean_white_assam.py", "r") as f:
    code = f.read()

# 1. Adjust map axes to leave clean headroom at the top for the outside banner
code = code.replace(
    'ax_m = fig_m.add_axes([0.08, 0.10, 0.78, 0.82], facecolor="#f8fafc")',
    'ax_m = fig_m.add_axes([0.08, 0.09, 0.78, 0.77], facecolor="#f8fafc")'
)

# 2. Adjust colorbar height to match
code = code.replace(
    'cbar_ax_m = fig_m.add_axes([0.88, 0.12, 0.022, 0.76])',
    'cbar_ax_m = fig_m.add_axes([0.88, 0.10, 0.022, 0.75])'
)

# 3. Remove the internal HUD box and internal title, and replace with top-center outside banner
old_hud_block = """        # Title without "GPM IMERG broadcast" text
        ax_m.set_title("MPAS-Atmosphere (15 km) — Assam Monsoon Rainfall Evolution",
                       color="#0f172a", fontsize=12, weight="bold", pad=8)
        ax_m.set_xlabel("Longitude (°E)", color="#334155", fontsize=9.5)
        ax_m.set_ylabel("Latitude (°N)", color="#334155", fontsize=9.5)

        # HUD Box
        hud_box = (
            f"DATE: {f_lbl}\\n"
            f"ASSAM MEAN: {f_mean:.1f} mm/day | MAX: {f_max:.1f} mm/day"
        )
        ax_m.text(0.03, 0.95, hud_box, transform=ax_m.transAxes,
                  fontsize=9, verticalalignment='top', color="#0f172a", weight="bold",
                  bbox=dict(boxstyle='round,pad=0.5', facecolor='#ffffff', edgecolor='#0284c7', alpha=0.95, lw=1.2))"""

new_hud_block = """        ax_m.set_xlabel("Longitude (°E)", color="#334155", fontsize=9.5)
        ax_m.set_ylabel("Latitude (°N)", color="#334155", fontsize=9.5)

        # Top Center Title (OUTSIDE the map)
        fig_m.text(0.47, 0.955, "MPAS-Atmosphere (15 km) — Assam Monsoon Rainfall Evolution",
                   color="#0f172a", fontsize=13, weight="bold", ha="center")

        # Top Center Timeline & Stats Banner (OUTSIDE the map, centered)
        timeline_banner = f"DATE: {f_lbl}   |   Assam State Mean: {f_mean:.1f} mm/day   |   Peak Cell: {f_max:.1f} mm/day"
        fig_m.text(0.47, 0.905, timeline_banner,
                   color="#0369a1", fontsize=9.5, weight="bold", ha="center",
                   bbox=dict(boxstyle="round,pad=0.4", facecolor="#f1f5f9", edgecolor="#0284c7", alpha=0.95, lw=1.2))"""

if old_hud_block in code:
    code = code.replace(old_hud_block, new_hud_block)
    with open("plot_clean_white_assam.py", "w") as f:
        f.write(code)
    print("Timeline banner moved outside to top-center successfully.")
else:
    print("Pattern search failed, applying fallback replace.")
    # Fallback direct replacement
    code = code.replace('ax_m.text(0.03, 0.95', '# ax_m.text(0.03, 0.95')
    with open("plot_clean_white_assam.py", "w") as f:
        f.write(code)
