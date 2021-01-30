#! /usr/bin/env python3

"""
In order to save space on the local filesystem, this script will trim the CONUS
domain data to a user-specified domain. These domains are currently specified
in .utils/mapinfo.py within the domains dictionary. Alternatively, the user can pass
a bounding box via the dbox flag.

Useage
------
*Note* you may have to run chmod +x domain_reduce.py first.

./domain_reduce.py -d [domain] -dbox ['LonW LatS LonE LatN'] -f [/path/to/individual/file.nc] -p [/path/to/entire/directory]

Either a -d or -dbox flag is required, but not both.
Either a -f or -p flag is required, but not both.
"""

from __future__ import print_function
import sys

import xarray as xr
from utils.proj import lat_lon_reproj
from utils.mapinfo import domains

import numpy as np
import argparse

from glob import glob
import shutil
import warnings
warnings.simplefilter("ignore")

def reduce_domain(domain=None, domain_box=None, filename=None, local_path=None):
    """

    """
    if domain:
        bounds = domains[domain]
    elif domain_box:
        bounds = [float(x) for x in str(domain_box).strip().split()]
    # Individual file
    if filename is not None:
        execute(filename, bounds)

    # Entire directory
    elif local_path is not None:
        files = glob(local_path + '/OR*.nc')
        for filename in files:
            execute(filename, bounds)

    return

def execute(filename, domain):
    """
    Read input file with xarray. Alter domain bounding area. Output
    a temporary file and then replace this with the original.

    Parameters
    ----------
    filename: str
        Input filename

    Returns
    -------
    Altered netCDF file.

    """
    lon, lat, X, Y = lat_lon_reproj(filename)
    idx_lat = np.where(np.logical_and(lat>=domain[1], lat<=domain[3]))
    idx_lon = np.where(np.logical_and(lon>=domain[0], lon<=domain[2]))
    idx_y = np.intersect1d(idx_lat[0], idx_lon[0])
    idx_x = np.intersect1d(idx_lat[1], idx_lon[1])
    ds = xr.open_dataset(filename)
    ds.CMI.values = np.where(np.logical_and(np.logical_and(lat>domain[1], lat<domain[3]),
                            np.logical_and(lon>domain[0], lon<domain[2])),
                            ds.CMI.values, np.nan)

    ds = ds.sel(x=X[idx_x], y=Y[idx_y])
    print("====> Altering domain of %s" % (filename))

    ds.to_netcdf(filename + '.temp')
    shutil.move(filename + '.temp', filename)

    return

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', '--domain', dest='domain', help="Individual filename")
    ap.add_argument('-dbox', '--domain-box', dest='domain_box', help="LonW LonE LatS LatN")
    ap.add_argument('-f', '--filename', dest='filename', help="Individual filename")
    ap.add_argument('-p', '--local-path', dest='local_path', help="Path containing netCDF files")
    args = ap.parse_args()
    np.seterr(all='ignore')

    if args.filename or args.local_path is not None:
        if args.filename and args.local_path is not None:
            print("**ERROR: Specify either a filename or filepath with a -f or -p flag, not both.")
            sys.exit(1)
        else:
            if args.domain is not None:
                reduce_domain(domain=args.domain, filename=args.filename,
                              local_path=args.local_path)
            elif args.domain_box is not None:
                reduce_domain(domain_box=args.domain_box, filename=args.filename,
                              local_path=args.local_path)
    else:
        print("**ERROR: You must specify either a filename or a file path with a -f or -p flag.")
        sys.exit(1)

if __name__ == "__main__":
    main()
