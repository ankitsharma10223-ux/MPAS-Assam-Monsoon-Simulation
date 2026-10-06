import numpy as np
from netCDF4 import Dataset
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

print("Loading MPAS daily rainfall from mpas_assam_rainfall.nc ...")
f_in = Dataset('mpas_assam_rainfall.nc', 'r')
lat_mpas = np.asarray(f_in.variables['lat'][:], dtype=np.float64)
lon_mpas = np.asarray(f_in.variables['lon'][:], dtype=np.float64)

# 1. Define Standard IMD 0.25-degree Grid over Assam & NE India
# Lat: 23.50 to 28.50 N, Lon: 89.50 to 96.50 E
grid_lat = np.arange(23.50, 28.75, 0.25)
grid_lon = np.arange(89.50, 96.75, 0.25)
grid_lons, grid_lats = np.meshgrid(grid_lon, grid_lat)
shape_2d = grid_lats.shape

target_lons = grid_lons.ravel()
target_lats = grid_lats.ravel()
ntarget = len(target_lats)

print(f"Target IMD 0.25° Grid Shape: {shape_2d} ({len(grid_lat)} lats x {len(grid_lon)} lons = {ntarget} points)")

# 2. Fast Vectorized IDW Interpolator (k=4 nearest neighbors on sphere)
def idw_interpolate(lon_s, lat_s, vals, lon_t, lat_t, k=4):
    cos_lat = np.cos(np.radians(0.5 * (lat_t[:, None] + lat_s[None, :])))
    dx = (lon_t[:, None] - lon_s[None, :]) * cos_lat
    dy = lat_t[:, None] - lat_s[None, :]
    d2 = dx**2 + dy**2 + 1e-12
    
    # 4 nearest neighbors
    idx = np.argpartition(d2, k, axis=1)[:, :k]
    d2_k = np.take_along_axis(d2, idx, axis=1)
    
    weights = 1.0 / np.maximum(d2_k, 1e-10)
    weights /= weights.sum(axis=1, keepdims=True)
    
    vals_k = np.take_along_axis(vals[None, :], idx, axis=1)
    return np.sum(vals_k * weights, axis=1)

# 3. Interpolate each day
days = ['rain_15_Jul', 'rain_16_Jul', 'rain_17_Jul', 'rain_18_Jul', 'rain_19_Jul', 'rain_5day_total']
interp_data = {}

for d in days:
    val = np.asarray(f_in.variables[d][:], dtype=np.float64)
    interp_1d = idw_interpolate(lon_mpas, lat_mpas, val, target_lons, target_lats, k=4)
    grid_val = interp_1d.reshape(shape_2d)
    interp_data[d] = grid_val
    print(f"Interpolated {d:17s} -> Min: {grid_val.min():5.2f} mm | Mean: {grid_val.mean():5.2f} mm | Max: {grid_val.max():5.2f} mm")

f_in.close()

# 4. Save to Regular NetCDF file
out_file = 'mpas_rainfall_imd0p25.nc'
f_out = Dataset(out_file, 'w', format='NETCDF4')

f_out.createDimension('lat', len(grid_lat))
f_out.createDimension('lon', len(grid_lon))

v_lat = f_out.createVariable('lat', 'f4', ('lat',))
v_lat.units = 'degrees_north'
v_lat.long_name = 'latitude'
v_lat[:] = grid_lat

v_lon = f_out.createVariable('lon', 'f4', ('lon',))
v_lon.units = 'degrees_east'
v_lon.long_name = 'longitude'
v_lon[:] = grid_lon

for d in days:
    v = f_out.createVariable(d, 'f4', ('lat', 'lon'))
    v.units = 'mm/day' if 'total' not in d else 'mm'
    v.long_name = f'MPAS remapped to IMD 0.25 deg grid ({d})'
    v[:, :] = interp_data[d]

f_out.title = 'MPAS-Atmosphere (15 km) Remapped to IMD 0.25-deg Gridded Resolution'
f_out.source = 'MPAS-Model v8.4.2 Simulation'
f_out.close()
print(f"\nSuccessfully wrote regular NetCDF: {out_file}")

# 5. Generate Plot on Regular IMD Grid
fig, axs = plt.subplots(2, 3, figsize=(16, 9))
axs = axs.flatten()
cmap = plt.cm.YlGnBu

for i, d in enumerate(days[:5]):
    im = axs[i].pcolormesh(grid_lon, grid_lat, interp_data[d], cmap=cmap, vmin=0, vmax=150, shading='auto')
    axs[i].set_title(f"MPAS (IMD 0.25° Grid): {d.replace('rain_', '').replace('_', ' ')}", fontsize=11, fontweight='bold')
    axs[i].set_xlabel("Longitude (°E)")
    axs[i].set_ylabel("Latitude (°N)")
    plt.colorbar(im, ax=axs[i], label="Rainfall (mm/day)", shrink=0.8)

# 6th panel: 5-Day Total
im_tot = axs[5].pcolormesh(grid_lon, grid_lat, interp_data['rain_5day_total'], cmap='turbo', vmin=0, vmax=450, shading='auto')
axs[5].set_title("MPAS (IMD 0.25° Grid): 5-Day Total", fontsize=11, fontweight='bold')
axs[5].set_xlabel("Longitude (°E)")
axs[5].set_ylabel("Latitude (°N)")
plt.colorbar(im_tot, ax=axs[5], label="Total (mm)", shrink=0.8)

plt.suptitle("MPAS-Atmosphere Interpolated to Standard IMD 0.25° Gridded Resolution (Assam)", fontsize=13, y=0.98)
plt.tight_layout()
plt.savefig('fig_mpas_imd0p25_rainfall.png', dpi=200, bbox_inches='tight')
print("Generated figure: fig_mpas_imd0p25_rainfall.png")
