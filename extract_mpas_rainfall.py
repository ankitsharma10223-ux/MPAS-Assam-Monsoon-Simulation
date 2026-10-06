import numpy as np
from netCDF4 import Dataset
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 1. Define IMD Evaluation Timestamps (03:00 UTC)
dates = [
    ('15-Jul', '2026-07-15_03.00.00', '2026-07-16_03.00.00'),
    ('16-Jul', '2026-07-16_03.00.00', '2026-07-17_03.00.00'),
    ('17-Jul', '2026-07-17_03.00.00', '2026-07-18_03.00.00'),
    ('18-Jul', '2026-07-18_03.00.00', '2026-07-19_03.00.00'),
    ('19-Jul', '2026-07-19_03.00.00', '2026-07-20_03.00.00'),
]

# 2. Read Mesh Coordinates from First File
f_init = Dataset(f"history.{dates[0][1]}.nc", 'r')
lat = np.degrees(f_init.variables['latCell'][:])
lon = np.degrees(f_init.variables['lonCell'][:])
ncells = len(lat)
f_init.close()

print(f"Loaded MPAS Assam mesh: {ncells} cells.")
print(f"Domain Bounds: Lat [{lat.min():.2f}, {lat.max():.2f}], Lon [{lon.min():.2f}, {lon.max():.2f}]")
print("=" * 70)

daily_rain = {}
summary_rows = []

# 3. Calculate 24-hr Rainfall for each IMD day
for label, t_start, t_end in dates:
    f1 = Dataset(f"history.{t_start}.nc", 'r')
    f2 = Dataset(f"history.{t_end}.nc", 'r')
    
    # Total rain = rainc (convective) + rainnc (grid-scale)
    rc1 = f1.variables['rainc'][0, :]
    rnc1 = f1.variables['rainnc'][0, :]
    rc2 = f2.variables['rainc'][0, :]
    rnc2 = f2.variables['rainnc'][0, :]
    
    d_rc  = np.maximum(0.0, rc2 - rc1)
    d_rnc = np.maximum(0.0, rnc2 - rnc1)
    d_tot = d_rc + d_rnc
    
    daily_rain[label] = d_tot
    mean_val = np.mean(d_tot)
    max_val = np.max(d_tot)
    
    summary_rows.append((label, mean_val, max_val, np.mean(d_rc), np.mean(d_rnc)))
    print(f"{label} (03Z-03Z): Mean = {mean_val:6.2f} mm/day | Max = {max_val:6.2f} mm/day | "
          f"Convective = {np.mean(d_rc):5.2f} mm | Stratiform = {np.mean(d_rnc):5.2f} mm")
    
    f1.close()
    f2.close()

# 4. Calculate 5-Day Cumulative Total
tot_5day = sum(daily_rain.values())
print("=" * 70)
print(f"5-Day Total (15-19 Jul): Domain Mean = {np.mean(tot_5day):6.2f} mm | Peak = {np.max(tot_5day):6.2f} mm")

# 5. Save Summary Table to CSV
with open('mpas_assam_rainfall_summary.csv', 'w') as f:
    f.write("Day,Mean_Rain_mm,Max_Rain_mm,Convective_Mean_mm,Stratiform_Mean_mm\n")
    for r in summary_rows:
        f.write(f"{r[0]},{r[1]:.2f},{r[2]:.2f},{r[3]:.2f},{r[4]:.2f}\n")
    f.write(f"5-Day_Total,{np.mean(tot_5day):.2f},{np.max(tot_5day):.2f},,\n")

# 6. Save Daily Rainfall to NetCDF
out_nc = Dataset('mpas_assam_rainfall.nc', 'w', format='NETCDF4')
out_nc.createDimension('nCells', ncells)
out_nc.createDimension('time', len(dates))

v_lat = out_nc.createVariable('lat', 'f4', ('nCells',))
v_lon = out_nc.createVariable('lon', 'f4', ('nCells',))
v_lat.units = 'degrees_north'
v_lon.units = 'degrees_east'
v_lat[:] = lat
v_lon[:] = lon

for label in daily_rain:
    v = out_nc.createVariable(f"rain_{label.replace('-', '_')}", 'f4', ('nCells',))
    v.units = 'mm/day'
    v.description = f'24-hr IMD accumulated rainfall for {label}'
    v[:] = daily_rain[label]

v_tot = out_nc.createVariable('rain_5day_total', 'f4', ('nCells',))
v_tot.units = 'mm'
v_tot.description = '5-day total accumulated rainfall (15-19 July 2026)'
v_tot[:] = tot_5day
out_nc.close()

# 7. Generate 6-Panel Visualization Map
fig, axs = plt.subplots(2, 3, figsize=(16, 10))
axs = axs.flatten()

levels = [0, 5, 15, 30, 50, 75, 100, 150, 200, 250]
cmap = plt.cm.YlGnBu

for i, (label, _, _) in enumerate(dates):
    sc = axs[i].scatter(lon, lat, c=daily_rain[label], s=8, cmap=cmap, vmin=0, vmax=150)
    axs[i].set_title(f"MPAS: {label} (24-hr IMD Rain)", fontsize=12, fontweight='bold')
    axs[i].set_xlabel("Longitude (°E)")
    axs[i].set_ylabel("Latitude (°N)")
    plt.colorbar(sc, ax=axs[i], label="Rainfall (mm/day)", shrink=0.8)

# 6th panel: 5-Day Cumulative Total
sc_tot = axs[5].scatter(lon, lat, c=tot_5day, s=8, cmap='turbo', vmin=0, vmax=500)
axs[5].set_title("MPAS: 15–19 July Total Rain", fontsize=12, fontweight='bold')
axs[5].set_xlabel("Longitude (°E)")
axs[5].set_ylabel("Latitude (°N)")
plt.colorbar(sc_tot, ax=axs[5], label="Total Rain (mm)", shrink=0.8)

plt.suptitle("MPAS-Atmosphere (15 km) — Assam Monsoon Rainfall Episode (15–19 July 2026)", fontsize=14, y=0.98)
plt.tight_layout()
plt.savefig('fig_mpas_assam_rainfall.png', dpi=200, bbox_inches='tight')
print("\nGenerated: mpas_assam_rainfall.nc, mpas_assam_rainfall_summary.csv, and fig_mpas_assam_rainfall.png")
