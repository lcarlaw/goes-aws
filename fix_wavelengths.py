#! /usr/bin/env python3

"""
This script can be used as a standalone command line operation, but is wrapped into the
main get_goes.py script. Its only purpose is to "fix" the wavelength metadata information
contained in the various GOES netCDF4 for proper display in the AWIPS WES2BRIDGE. For some
reason, various channel wavelengths are 0.01-0.03 microns off from what AWIPS "expects" to
see and therefore will not properly decode the raw netCDF4 files that are stored on the
AWS.

Useage
------
*Note* you may have to run chmod u+x fix_wavelengths.py first.

./fix_wavelengths.py -f [/path/to/individual/file.nc] -p [/path/to/entire/directory]

Either a -f or -p flag is required, but not both.

Required Libraries
------------------
conda install xarray
conda install netcdf4

This has been tested on Python 3+ but *should* work with Python 2 as well,
although no guarantees are made.
"""

from __future__ import print_function
import sys

import xarray as xr
from utils.band_info import band_values

import numpy as np
import argparse

from glob import glob
import shutil

import warnings
warnings.simplefilter("ignore")

def fix_data(filename=None, local_path=None):
    """
    Function controls passing of single files or entire directories to be
    altered.

    Parameters
    ----------
    filename: str
        Input filename
    local_path: str
        Input path (directory) with or without trailing '/'

    """
    # Individual file
    if filename is not None:
        execute(filename)

    # Entire directory
    elif local_path is not None:
        files = glob(local_path + '/OR_*.nc')
        for filename in files:
            execute(filename)

    return

def execute(filename):
    """
    Read input file with xarray. Alter wavelength information if needed. Output
    a temporary file and then replace this with the original.

    Parameters
    ----------
    filename: str
        Input filename

    Returns
    -------
    Altered netCDF file.

    """
    ds = xr.open_dataset(filename)
    wavelength = ds.band_wavelength.values[0]
    band_id = ds.band_id.values[0]

    awips_expected = band_values[band_id]
    if band_id != awips_expected:
        print("====> Changing band_wavelength value from %s um to %s um" % \
              (wavelength, awips_expected))
        ds.assign_coords(band_wavelength=awips_expected)
        ds.to_netcdf(filename + '.temp')

        arg = '%s.temp %s' % (filename, filename)
        shutil.move(filename + '.temp', filename)

    return

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--filename', dest='filename', help="Individual filename")
    ap.add_argument('-p', '--local-path', dest='local_path', help="Path containing netCDF files")
    args = ap.parse_args()
    np.seterr(all='ignore')

    if args.filename or args.local_path is not None:
        if args.filename and args.local_path is not None:
            print("**ERROR: Specify either a filename or filepath with a -f or -p flag, not both.")
            sys.exit(1)
        else:
            fix_data(filename=args.filename,
                     local_path=args.local_path
                    )
    else:
        print("**ERROR: You must specify either a filename or a file path with a -f or -p flag.")
        sys.exit(1)

if __name__ == "__main__":
    main()
