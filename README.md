# goes-aws
Repository to automate downloading of GOES-16/17 data for general use or in AWIPS WES cases. Abilities built in to create reduced domains (still debugging this one) and manually alter wavelength metadata.

This README is specifically built out from an end-to-end test performed for a convective WES case.

## Setup Notes
### Initial environment creation

The setup proceeds using Anaconda, as well as assuming a completely vanilla Python3 install.  I've also edited my `~/.condarc` file to add conda-forge to the default channels.

```
conda create --name aws python=3.7
conda activate aws
conda install s3fs xarray netcdf4
```

Export the conda `.yml` file with:

```
conda env export --from-history -f environment.yml
```

### Creating the base environment
You should be able to create an Anaconda environment with the following command:

```
conda env create --name envname --file environment.yml
```

## Code execution
### Download satellite netCDF data
The following will download all 16 channels from the GOES-16 ABI archive on the AWS. Note: It looks like AWIPS expects the satellite files to be a specific size (x, y). In our testing, we found that the WES would not display files that had been truncated to a smaller domain (at least with the current methodology utilizing xarray). For the time being, do not specify `domain` or `dbox` flags for use on the WES box.

`python get_goes.py YYYY-mm-dd/HHMM YYYY-mm-dd/HHMM -p /Users/leecarlaw/satellite_data/foo -b all -G econus`

Upload this data to Google Drive.

### Processing data on the WES
Once the GOES netCDF files have been migrated to the WES box, follow these steps to load them into a case and convert them into AWIPS-readable hdf5 files (Kevin D. will be working on this documentation):

- rawPlay
- CMIP xml data
- case creation
- etc.

### To-Dos:
1. Figure out why there are duplicate wavelengths for certain channels
    * Dale had earlier done some work updating some .xml files?
2. Were we able to remove the USER-override file?
    * CAVE > Menus > Satellite > goesr > goesrByChannel.xml
3. Work on reduced domain problem
