# goes-aws
Repository to automate downloading of GOES-16/17 data for general use or in AWIPS WES cases. Abilities built in to create reduced domains (still debugging this one) and manually alter wavelength metadata. The main script will spin up 8 parallel processes to speed up download times from the AWS.

This README is specifically built out from an end-to-end test performed for a convective WES case.

![](https://raw.githubusercontent.com/lcarlaw/goes-aws/master/GOESdata.png)

## Setup Notes
### Initial environment creation

The setup proceeds using Anaconda, as well as assuming a completely vanilla Python3 install.  I've edited my `~/.condarc` file to add conda-forge to the default channels.

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
The following will download all 16 channels from the GOES-16 ABI archive on the AWS. The full suite of ABI channels is needed for the creation of RGBs within AWIPS. Note: It looks like AWIPS expects the satellite files to be a specific size (x, y). In our testing, we found that the WES would not display files that had been truncated to a smaller domain (at least with the current methodology utilizing xarray). For the time being, do not specify `domain` or `dbox` flags for use on the WES box.

`python get_goes.py YYYY-mm-dd/HHMM YYYY-mm-dd/HHMM -p /Users/leecarlaw/satellite_data/foo -b all -G econus`

Upload this data to Google Drive.

#### To Dos:
- Get local/limited domains working (likely an issue with NaNs in the original files we had?)
- GLM data archive

## Processing data on the WES
Once the GOES netCDF files have been migrated to the WES box, follow these steps to load them into a case and convert them into AWIPS-readable hdf5 files.

### Prerequisite CMIP xml files
On your WES-2 Bridge workstation, open a terminal window and look for the following directory: `/awips2/edex/data/utility/common_static/site/LOT/satellite/goesr/descriptions/Level2`, where XXX is your site ID (i.e. LOT). If your workstation is configured, you will see several files in this window. The important files are the CMIPCommonDescription.xml, the Channel*.xml and the GOES*Sectors.xml files. These files are included in this repo in the `./CMIP` directory.

### Restart EDEX
Use WES-2 Bridge to start up the EDEX_00 instance if it is not running. It may not be a bad idea to reset EDEX if you have reprocessed a different case recently, but we have not had problems with this locally. You will need to Restart EDEX_00 if you installed a new CMIP file and will allow EDEX to read in the new configurations.

### Running RawPlay
Run rawPlay6.py (or whatever is our latest version i.e. rawPlay5.py). We need to run the rawPlay6.py software with a special flag that enables the CLASS functionality which is the -c switch.  (From here on out, the process is similar as detailed in the WDTD guides on reprocessing data training.weather.gov/wdtd/tools/wes2/training.php) and select Reprocessing Guide for more details.  

```cd /w2b/util
./rawPlay6.py -c /data/archiver
```

Use the WES-2 Bridge “New Case” function (File -> NewCase). In this GUI, the case type is `Ingested Data_EDEX_00` and the data type is `Satellite`.

### Creating the case
Copy the `satellite` directory from your test case to an actual case (Dale noted duplicates in there, we will have to check this out (both 6.93 and 6.95 for example).

```
cd /data1/wes_cases/Class_Satellite_Data/Processed/satellite
cp -r * /data1/wes_cases/<case name>/Processed/satellite
cd /data1/wes_cases/<case name>/Processed/satelllite
chmod g+w *
```

Update the `caseMetaData.xml` of the new case that did not initially have satellite data. This will allow satellite data to be selected as a Data Type for the case.

```
cd /data1/wes_cases/<case name>
gedit caseMetaData.xml (or vi) and add an entry for Satellite
```

Unload and Reload your case from WES-2 Bridge: The data will not work unless you unload and reload the case if it was previously loaded.

Debugging (Check the following files in the Localization Perspective) - We have some duplicate wavelengths, so we need to investigate these. These also are good files to look at if the menus are not displaying correctly.
