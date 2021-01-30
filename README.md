# goes-aws
Repository to automate downloading of GOES-16/17 data for use in AWIPS WES cases. Abilities built in to create reduced domains and manually alter wavelength metadata.

This README is built out from an end-to-end test performed for a convective WES case.

## Setup Notes
### Initial environment creation [ for Lee ]

The setup here proceeds using Anaconda, as well as assuming a completely vanilla Python3 install.  I've also edited my `~/.condarc` file to add conda-forge to the default channels.

```
conda create --name aws python=3.7
conda activate aws
conda install s3fs xarray netcdf4
```

Export the conda `.yml` file with:

```
conda env export --from-history -f environment.yml
```

### Creating the base environment [ other users ]
You should be able to create an Anaconda environment with the following command:

```
conda env create --name envname --file environment.yml
```

## Code execution

`python get_goes.py YYYY-mm-dd/HHMM YYYY-mm-dd/HHMM -p /Users/leecarlaw/satellite_data/summer_wes -b all -dbox '-96 37 -82 47'`
