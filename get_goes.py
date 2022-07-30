# get_goes.py
#
# NOTE: If using this to download data for processing on the WES, you cannot use the 
# -d or -dbox flags as AWIPS expects the data arrays to be specific, pre-defined sizes.
#
# Useage:
#   python get_goes.py 2020-05-23/1200 -e 2020-05-24-/0300 -p /Users/leecarlaw/satellite/20200524 -b 2,5,10 -d MW
#   python get_goes.py YYYY-mm-dd/HHMM YYYY-mm-dd/HHMM -p /Users/leecarlaw/satellite_data/summer_wes -b all

import sys, os
from subprocess import call
from subprocess import Popen, PIPE

from datetime import datetime, timedelta
import argparse
import numpy as np
from collections import defaultdict
import itertools

import s3fs
import re

from multiprocessing import Pool

try:
    from shutil import which
except ImportError:
    from distutils.spawn import find_executable as which

# Logic to find wget or curl on the system. Only needed for < Goe 16
WGET = which('wget')
if not WGET:
    CURL = which('curl')
if not WGET and not CURL:
    raise ValueError("Neither wget nor curl found on the system. Exiting")

#[OI][RT]_ABI-L2-\w{4}(C|F|M1|M2)-M\dC%s_G\d\d_s\d{14}_e\d{14}_c\d{14}.nc
regex_str = "_s([\d]{14})"
metadata = {
    'econus': {
        'sat_num': 16,
        'domain': 'C',
    },
    'emeso-1': {
        'sat_num': 16,
        'domain': 'M1',
    },
    'emeso-2': {
        'sat_num': 16,
        'domain': 'M2',
    },
    'wconus': {
        'sat_num': 17,
        'domain': 'C',
    },
    'wmeso-1': {
        'sat_num': 17,
        'domain': 'M1',
    },
    'wmeso-2': {
        'sat_num': 17,
        'domain': 'M2',
    },
}
def get_data_aws(start_time, end_time, local_path=None, bands=None, glm=None, domain=None,
              domain_box=None, goes_domain=None):
    """
    Query the AWS database for user-requested GOES 16 data and download to
    specified path. Corrects the wavelength issue in the AWS versus AWIPS
    files for bands 3,4,6,9,11,13,14,15, and 16

    Parameters
    ----------
    start_time : string
        Initial time for data. Form is YYYYMMDD/HH
    end_time : string
        End time for data. Form is YYYYMMDD/HH

    Other Parameters
    ----------------
    local_path : string
        Path to download files to. If not specified, creates a director in the PWD called
        DATA_YYYmmdd_HHMM
    bands : str or ints
        Listing of ABI bands to download. Form is 1,2,3...,16 or all
    glm : bool
        Whether to download GLM data. If so, set to True
    domain : string
        String corresponding to a key in the mapinfo.py domains dictionary
    domain_box : string
        String in the form 'LonW LatS LonE LatN'
    goes_domain : string
        [econus | emeso-1 | emeso-2 | wconus | wmeso-1 | wmeso-2]

    **NOTE** For WES cases, the full domains must be downloaded (i.e. do not specify
    domain or domain_box).

    """
    fs = s3fs.S3FileSystem(anon=True)
    if not goes_domain: goes_domain = 'econus'

    # If no local path specified in args, create a directory based on the current time.
    if not local_path:
        curr_date = datetime.strftime(datetime.now(), '%Y%m%d-%H%M')
        local_path = os.environ['PWD'] + '/DATA_' + curr_date
        print("Creating output directory: ", local_path)
        if not os.path.exists(local_path): os.mkdir(local_path)

    # Determine the date directories we'll need to search through on the AWS.
    # Individual days are stored as Julian Dates, so take care of that here.
    dt_start = datetime.strptime(start_time, '%Y-%m-%d/%H%M')
    dt_end = datetime.strptime(end_time, '%Y-%m-%d/%H%M')

    time_dict = {'years':[], 'jdays':[], 'hours':[]}
    dt = dt_start
    n_hours = 0
    previous_hour = -999
    while dt <= dt_end:
        dt = dt + timedelta(minutes=1)
        if dt.hour != previous_hour:
            time_dict['years'].append(str(dt.year).zfill(4))
            time_dict['jdays'].append(str(dt.timetuple().tm_yday).zfill(3))
            time_dict['hours'].append(str(dt.hour).zfill(2))
            n_hours += 1
        previous_hour = dt.hour

    # Determine which bands we need to search for
    band_names = []
    if bands is not None:
        if bands != 'all':
            for band in bands.split(','):
                band_names.append('M3C' + str(band).zfill(2))
                band_names.append('M6C' + str(band).zfill(2))
        else:
            for band in range(1, 17):
                band_names.append('M3C' + str(band).zfill(2))
                band_names.append('M6C' + str(band).zfill(2))

    if glm in ['true', 'True', 't', 'T']: band_names.append('LCFA')

    # Loop through the data structure and find file names
    META = metadata[goes_domain]
    head1 = "noaa-goes%s/ABI-L2-CMIP%s/" % (META['sat_num'], META['domain'][0])
    head2 = "noaa-goes16/GLM-L2-LCFA/"
    files = []
    for hr in range(0, n_hours):
        tail = time_dict['years'][hr] + '/' + time_dict['jdays'][hr] + '/' + \
               time_dict['hours'][hr]
        f1 = fs.ls(head1 + tail)
        f2 = fs.ls(head2 + tail)
        files.append(f1 + f2)
    files = list(itertools.chain.from_iterable(files))

    # Pare down to the user-requested data. Kind of hacky.
    downloads = defaultdict(list)
    download_size = 0.
    for band in band_names:
        for f in files:
            if f.find(band) > 0:
                idx = f.find("OR_ABI-L2-CMIP%s-" % (META['domain']))
                #idx = f.index("OR_")
                if idx > 0:
                    fname = f[idx:]
                    # Grab all the scan time strings following the regex pattern & convert
                    # to datetime objects. We're ignoring the last digit which is the
                    # tenth of a second.
                    scan_string = re.findall(regex_str, f)[0][0:-1]
                    scan_dt = datetime.strptime(scan_string, '%Y%j%H%M%S')

                    if dt_start <= scan_dt <= dt_end:
                        downloads[f] = local_path + '/' + fname
                        download_size += fs.info(f)['size']

    # Query user if they'd like to continue based on expected download size
    for key in downloads.keys():
        idx = key.index('OR_')
    print("==>Number of requested files: ", len(downloads.keys()))
    str1 = "==>Requested download BEFORE domain reducing is ~ "
    str2 = "MB. Continue? [y|n] *hit ENTER*"
    print(str1, round(download_size / 1000000.), str2)
    resp = input()

    if domain is not None:
        domains = [domain for i in range(len(list(downloads.keys())))]
        domain_boxes = [None for i in range(len(list(downloads.keys())))]
    else:
        domain_boxes = [domain_box for i in range(len(list(downloads.keys())))]
        domains = [None for i in range(len(list(downloads.keys())))]

    if resp in ['y', 'Y', 'yes']:
        timeit = datetime.now()
        with Pool(8) as pool:
            pool.starmap(download_aws, zip(list(downloads.keys()),
                                           list(downloads.values()),
                                           domains,
                                           domain_boxes))
        timeit = (datetime.now()-timeit).seconds
        print("Download took: %s minutes" % (int(timeit / 60.)))
    else:
        print("==================")
        print("===  Goodbye!  ===")
        print("==================")
        sys.exit(0)
    return

def download_aws(url, filename, domain, dbox):
    """
    Perform downloading of netCDF files from AWS

    Parameters
    ----------
    url : string
        Full URL to online netcdf file
    filename : string
        Path and name to store on local system

    Other Parameters
    ----------------
    domain : string
        String corresponding to a key in the mapinfo.py domains dictionary
    domain_box : string
        String in the form 'LonW LatS LonE LatN'

    """
    fs = s3fs.S3FileSystem(anon=True)
    print("Downloading: ", filename)
    fs.get(url, filename)

    # Pass this file to fix_wavelengths for proper AWIPS-read in
    arg = './fix_wavelengths.py -f %s' % (filename)
    call(arg, shell=True)

    reduce = False
    if domain is not None:
        arg = "./domain_reduce.py -d %s -f %s" % (domain, filename)
        reduce = True
    elif dbox is not None:
        arg = "./domain_reduce.py -dbox '%s' -f %s" % (dbox, filename)
        reduce = True
    if reduce: call(arg, shell=True)

def grab_data_goes_N(start_time, end_time, local_path=None, domain=None, domain_box=None):
    """
    Download gridded GOES-N data

    Parameters
    ----------
    start_time : string
        Initial time for data. Form is YYYYMMDD/HH
    end_time : string
        End time for data. Form is YYYYMMDD/HH
    local_path : string
        Path to download files to. Defaults to pwd.

    """
    base = "https://www.ncei.noaa.gov/data/gridsat-goes/access/conus"

    # If no local path specified in args, create a directory based on the
    # current time.
    if not local_path:
        curr_date = datetime.strftime(datetime.now(), '%Y%m%d-%H%M')
        local_path = os.environ['PWD'] + '/DATA_' + curr_date
        print("Creating output directory: ", local_path)
        if not os.path.exists(local_path): os.mkdir(local_path)

    # Determine the date directories we'll need to search through on the AWS.
    # Individual days are stored as Julian Dates, so take care of that here.
    dt_start = datetime.strptime(start_time, '%Y-%m-%d/%H%M')
    dt_end = datetime.strptime(end_time, '%Y-%m-%d/%H%M')

    files = []
    dt = dt_start
    while dt <= dt_end:
        fname = "GridSat-CONUS.goes13.%s.v01.nc" % (dt.strftime('%Y.%m.%d.%H%M'))
        url = "%s/%s/%s/%s" % (base, str(dt.year), str(dt.month).zfill(2), fname)
        #try:
        if WGET:
            p = Popen([WGET, '-O', '%s/%s' % (local_path, fname), url])
        elif CURL:
            p = Popen([CURL, '-o', '%s/%s' % (local_path, fname), url], stderr=PIPE)
        p.wait()
        #except:
        #    pass
        dt += timedelta(minutes=15)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('start_time', help="First scan time [YYYY-MM-DD/HHmm]")
    ap.add_argument('end_time', help="Last scan time [YYYY-MM-DD/HHmm]")
    ap.add_argument('-p', '--local-path', dest='local_path', help="Path to store files")
    ap.add_argument('-b', '--bands', dest='bands', help="ABI bands 1,2,3,...,16, all")
    ap.add_argument('-g', '--glm', dest='glm', help="[True]. Include GLM data")
    ap.add_argument('-G', '--goes_domain', dest='goes_domain', help="econus,wconus,emeso-1,emeso-2,wmeso-1,wmeso-2")
    ap.add_argument('-d', '--domain', dest='domain', help="Reduce to a domain")
    ap.add_argument('-dbox', '--domain-box', dest='domain_box', help="LonW LatS LonE LatN")
    args = ap.parse_args()
    np.seterr(all='ignore')

    # Check the start and end time date formatting
    try:
        start = datetime.strptime(args.start_time, '%Y-%m-%d/%H%M')
        end = datetime.strptime(args.end_time, '%Y-%m-%d/%H%M')
    except:
        print("**Error: Badly formatted start and/or end times. Exiting**\n")
        sys.exit(1)

    epoch = datetime(2017, 3, 1, 0, 0)

    # GOES-N 13,15
    if end < epoch:
        grab_data_goes_N(args.start_time,
                         args.end_time,
                         local_path=args.local_path,
                         domain=args.domain,
                         domain_box=args.domain_box
                         )
    # GOES-R
    elif start >= epoch:
        if args.bands is not None or args.glm is not None:
            get_data_aws(args.start_time,
                         args.end_time,
                         local_path=args.local_path,
                         bands=args.bands,
                         glm=args.glm,
                         domain=args.domain,
                         domain_box=args.domain_box,
                         goes_domain=args.goes_domain
                         )
        else:
            print("**Error: No ABI bands or GLM data to download.**")
            sys.exit(1)

    elif start < epoch and end >= epoch:
        print("Dates straddling GOES-N and GOES-R Data. Logic not implemented yet")

if __name__ == "__main__":
    main()
