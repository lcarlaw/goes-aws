import xarray as xr
import pandas as pd
import numpy as np

def lat_lon_reproj(file_):
    g16nc = xr.open_dataset(file_).load()
    band_id = g16nc.band_id.values

    # Timestamp
    dt = g16nc.t.values
    ts = pd.to_datetime(str(dt))
    date_str = ts.strftime('%Y%m%d%H%M')

    proj_info = g16nc.goes_imager_projection
    lon_origin = proj_info.longitude_of_projection_origin
    H = proj_info.perspective_point_height+proj_info.semi_major_axis
    r_eq = proj_info.semi_major_axis
    r_pol = proj_info.semi_minor_axis

    lat_rad = g16nc.variables['x'][:].values
    lon_rad = g16nc.variables['y'][:].values
    X = lat_rad
    Y = lon_rad
    g16nc.close()

    lat_rad,lon_rad = np.meshgrid(lat_rad,lon_rad)
    lambda_0 = (lon_origin*np.pi)/180.0

    a_var = np.power(np.sin(lat_rad),2.0) + (np.power(np.cos(lat_rad),2.0)*(np.power(np.cos(lon_rad),2.0)+(((r_eq*r_eq)/(r_pol*r_pol))*np.power(np.sin(lon_rad),2.0))))
    b_var = -2.0*H*np.cos(lat_rad)*np.cos(lon_rad)
    c_var = (H**2.0)-(r_eq**2.0)

    r_s = (-1.0*b_var - np.sqrt((b_var**2)-(4.0*a_var*c_var)))/(2.0*a_var)

    s_x = r_s*np.cos(lat_rad)*np.cos(lon_rad)
    s_y = - r_s*np.sin(lat_rad)
    s_z = r_s*np.cos(lat_rad)*np.sin(lon_rad)

    # latitude and longitude projection for plotting data on traditional lat/lon maps
    lat = (180.0/np.pi)*(np.arctan(((r_eq*r_eq)/(r_pol*r_pol))*((s_z/np.sqrt(((H-s_x)*(H-s_x))+(s_y*s_y))))))
    lon = (lambda_0 - np.arctan(s_y/(H-s_x)))*(180.0/np.pi)

    return lon, lat, X, Y
