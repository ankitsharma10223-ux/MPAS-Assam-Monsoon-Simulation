import re

with open("plot_clean_white_assam.py", "r") as f:
    code = f.read()

# Replace the video generation block
old_block = """    os.makedirs("movie_light_temp", exist_ok=True)
    fig_m = plt.figure(figsize=(11, 7), facecolor="#ffffff")
    img_files = []

    for f_idx, (f_data, f_lbl, (f_mean, f_max)) in enumerate(zip(all_frames, all_lbls, all_stats)):
        fig_m.clf()
        ax_m = fig_m.add_axes([0.08, 0.10, 0.78, 0.82], facecolor="#f8fafc")"""

new_block = """    os.makedirs("movie_light_temp", exist_ok=True)
    fig_m = plt.figure(figsize=(11, 7), facecolor="#ffffff")
    ax_m = fig_m.add_axes([0.08, 0.10, 0.78, 0.82], facecolor="#f8fafc")
    cbar_ax_m = fig_m.add_axes([0.88, 0.12, 0.022, 0.76])
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
        ax_m.set_facecolor("#f8fafc")"""

if old_block in code:
    code = code.replace(old_block, new_block)
    # Remove the per-frame colorbar creation at line 348
    code = code.replace("""        # Colorbar embedded directly into video frame
        cbar_ax_m = fig_m.add_axes([0.88, 0.12, 0.022, 0.76])
        cb_m = fig_m.colorbar(cf_m, cax=cbar_ax_m, orientation="vertical", extend='max')
        cb_m.set_label("Precipitation (mm / day)", color="#0f172a", fontsize=9.5, weight="bold")
        cb_m.ax.yaxis.set_tick_params(color="#334155", labelsize=8.5)
        cb_m.outline.set_edgecolor("#cbd5e1")""", "# Colorbar handled statically outside loop")
    with open("plot_clean_white_assam.py", "w") as f:
        f.write(code)
    print("Updated plot_clean_white_assam.py successfully.")
else:
    print("Block pattern mismatch, rewrite directly.")
