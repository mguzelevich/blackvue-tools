#!/bin/python

import argparse
import datetime
import json
import os
import pathlib
import re
import select
import subprocess
import sys

from time import gmtime, strftime

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TS = strftime("%Y%m%d_%H%M%S", gmtime())
DRY_RUN = True

# [1500310610235]$GPGLL,5355.68249,N,02738.67852,E,135648.00,A,A*63
LINE_RE_STRING = r'\[([0-9]+)\]\$GP([A-Z]+),(.+)'
LINE_RE = re.compile(LINE_RE_STRING)


def exec_cmd(cwd, cmd, *args):
    logger.debug('exec_cmd %s %s %s', cwd, cmd, args)
    cmdArgs = [cmd]
    cmdArgs.extend(list(*args))
    logger.debug('exec_cmd %s', cmdArgs)
    process = subprocess.run(' '.join(cmdArgs), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    try:
        process.check_returncode()
    except subprocess.CalledProcessError as e:
        logger.error("exec_cmd [%s] out=`%s` err=`%s` e=`%s`", process.returncode, process.stdout, process.stderr, e)
    else:
        logger.debug("exec_cmd [%s] out=`%s` err=`%s`", process.returncode, process.stdout, process.stderr)

    return (process.returncode,
            process.stdout.decode('utf-8'),
            process.stderr.decode('utf-8'))


def merge_gps(input_data):
    keys = sorted(input_data.keys())
    chunks = {}

    start_ts = keys[0] if len(keys) else None
    last_ts = None

    chunk = {
        'start': datetime.datetime.fromtimestamp(start_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'points': [],
    }

    for i, ts in enumerate(keys):
        if last_ts and ts - last_ts > 5000:
            chunk['end'] = datetime.datetime.fromtimestamp(last_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            chunks[(start_ts, last_ts)] = chunk
            chunk = {
                'start': datetime.datetime.fromtimestamp(start_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'points': [],
            }
            start_ts = ts
        chunk['points'].append(input_data[ts])
        last_ts = ts
    if chunk:
        chunk['end'] = datetime.datetime.fromtimestamp(last_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        chunks[(start_ts, last_ts)] = chunk

    for i, ch in enumerate(chunks):
        logger.debug('%s. %s', i, (chunks[ch]['start'], chunks[ch]['end']))

    print(json.dumps(chunks[ch], indent='  '))


def handler_dafault(cmd, *args):
    logger.warning('unknown command [%s] %s', cmd, args)


"""
$GPRMC,220516,A,5133.82,N,00042.24,W,173.8,231.8,130694,004.2,W*70
         1    2    3    4    5     6    7    8      9     10  11 12

      1   220516     Time Stamp
      2   A          validity - A-ok, V-invalid
      3   5133.82    current Latitude
      4   N          North/South
      5   00042.24   current Longitude
      6   W          East/West
      7   173.8      Speed in knots
      8   231.8      True course
      9   130694     Date Stamp
      10  004.2      Variation
      11  W          East/West
      12  *70        checksum

$GPRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,x.x,a*hh
1    = UTC of position fix
2    = Data status (V=navigation receiver warning)
3    = Latitude of fix
4    = N or S
5    = Longitude of fix
6    = E or W
7    = Speed over ground in knots
8    = Track made good in degrees True
9    = UT date
10   = Magnetic variation degrees (Easterly var. subtracts from true course)
11   = E or W
12   = Checksum
"""


def handler_RMC(cmd, *args):
    (
        fix_time,           # Fix taken at 12:35:19 UTC
        status,             # Status A=active or V=Void.
        lat,                # Latitude 48 deg 07.038' N
        north_south,        # North/South
        lng,                # Longitude 11 deg 31.000' E
        east_west,          # East/West
        speed,              # Speed over the ground in knots
        angle,              # Track angle in degrees True
        date,               # Date - 23rd of March 1994
        x1,                 # UNKNOWN FIELD
        magnetic_variation,  # Magnetic Variation
        fix_type            # fix_type
    ) = args
    if x1:
        raise RuntimeError(x1)

    return {
        'fix_time': fix_time,
        'status': status,
        'lat': (lat, north_south),
        'lng': (lng, east_west),
        'speed': speed,
        'angle': angle,
        'date': date,
        'magnetic_variation': magnetic_variation,
        'fix_type': fix_type,
    }


"""
eg1. $GPVTG,360.0,T,348.7,M,000.0,N,000.0,K*43
eg2. $GPVTG,054.7,T,034.4,M,005.5,N,010.2,K

           054.7,T      True track made good
           034.4,M      Magnetic track made good
           005.5,N      Ground speed, knots
           010.2,K      Ground speed, Kilometers per hour


eg3. $GPVTG,t,T,,,s.ss,N,s.ss,K*hh
1    = Track made good
2    = Fixed text 'T' indicates that track made good is relative to true north
3    = not used
4    = not used
5    = Speed over ground in knots
6    = Fixed text 'N' indicates that speed over ground in in knots
7    = Speed over ground in kilometers/hour
8    = Fixed text 'K' indicates that speed over ground is in kilometers/hour
9    = Checksum
The actual track made good and speed relative to the ground.

$--VTG,x.x,T,x.x,M,x.x,N,x.x,K
x.x,T = Track, degrees True 
x.x,M = Track, degrees Magnetic 
x.x,N = Speed, knots 
x.x,K = Speed, Km/hr
"""


def handler_VTG(cmd, *args):
    (
        track_mode,     # Track made good
        true_north,     # Fixed text 'T' indicates that track made good is relative to true north
        x1,             # not used
        x2,             # not used
        speed_kn,       # Speed over ground in knots
        speed_kn_sign,  # Fixed text 'N' indicates that speed over ground in in knots
        speed_kmh,      # Speed over ground in kilometers/hour
        speed_kmh_sign,  # Fixed text 'K' indicates that speed over ground is in kilometers/hour
        fix_type        # fix_type
    ) = args
    # if x1 or x2:
    #     raise RuntimeError(cmd, args, x1, x2)

    return {
        'track_mode': track_mode,
        'true_north': true_north,
        'speed_kn': speed_kn,
        'speed_kmh': speed_kmh,
        'fix_type': fix_type,
    }

"""
eg2. $--GGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,x.x,x.x,M,x.x,M,x.x,xxxx
hhmmss.ss = UTC of position 
llll.ll = latitude of position
a = N or S
yyyyy.yy = Longitude of position
a = E or W 
x = GPS Quality indicator (0=no fix, 1=GPS fix, 2=Dif. GPS fix) 
xx = number of satellites in use 
x.x = horizontal dilution of precision 
x.x = Antenna altitude above mean-sea-level
M = units of antenna altitude, meters 
x.x = Geoidal separation
M = units of geoidal separation, meters 
x.x = Age of Differential GPS data (seconds) 
xxxx = Differential reference station ID 

eg3. $GPGGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,x.x,x.x,M,x.x,M,x.x,xxxx*hh
1    = UTC of Position
2    = Latitude
3    = N or S
4    = Longitude
5    = E or W
6    = GPS quality indicator (0=invalid; 1=GPS fix; 2=Diff. GPS fix)
7    = Number of satellites in use [not those in view]
8    = Horizontal dilution of position
9    = Antenna altitude above/below mean sea level (geoid)
10   = Meters  (Antenna height unit)
11   = Geoidal separation (Diff. between WGS-84 earth ellipsoid and
       mean sea level.  -=geoid is below WGS-84 ellipsoid)
12   = Meters  (Units of geoidal separation)
13   = Age in seconds since last update from diff. reference station
14   = Diff. reference station ID#
15   = Checksum
"""


def handler_GGA(cmd, *args):
    #    (
    #    ) = args

    return {
    }


"""
eg1. $GPGSA,A,3,,,,,,16,18,,22,24,,,3.6,2.1,2.2*3C
eg2. $GPGSA,A,3,19,28,14,18,27,22,31,39,,,,,1.7,1.0,1.3*35


1    = Mode:
       M=Manual, forced to operate in 2D or 3D
       A=Automatic, 3D/2D
2    = Mode:
       1=Fix not available
       2=2D
       3=3D
3-14 = IDs of SVs used in position fix (null for unused fields)
15   = PDOP
16   = HDOP
17   = VDOP
"""


def handler_GSA(cmd, *args):
    #    (
    #    ) = args

    return {
    }


"""
GPS Satellites in view

eg. $GPGSV,3,1,11,03,03,111,00,04,15,270,00,06,01,010,00,13,06,292,00*74
    $GPGSV,3,2,11,14,25,170,00,16,57,208,39,18,67,296,40,19,40,246,00*74
    $GPGSV,3,3,11,22,42,067,42,24,14,311,43,27,05,244,00,,,,*4D


    $GPGSV,1,1,13,02,02,213,,03,-3,000,,11,00,121,,14,13,172,05*67


1    = Total number of messages of this type in this cycle
2    = Message number
3    = Total number of SVs in view
4    = SV PRN number
5    = Elevation in degrees, 90 maximum
6    = Azimuth, degrees from true north, 000 to 359
7    = SNR, 00-99 dB (null when not tracking)
8-11 = Information about second SV, same as field 4-7
12-15= Information about third SV, same as field 4-7
16-19= Information about fourth SV, same as field 4-7
"""


def handler_GSV(cmd, *args):
    #    (
    #    ) = args

    return {
    }


"""
Geographic Position, Latitude / Longitude and time.

eg1. $GPGLL,3751.65,S,14507.36,E*77
eg2. $GPGLL,4916.45,N,12311.12,W,225444,A


           4916.46,N    Latitude 49 deg. 16.45 min. North
           12311.12,W   Longitude 123 deg. 11.12 min. West
           225444       Fix taken at 22:54:44 UTC
           A            Data valid


eg3. $GPGLL,5133.81,N,00042.25,W*75
               1    2     3    4 5

      1    5133.81   Current latitude
      2    N         North/South
      3    00042.25  Current longitude
      4    W         East/West
      5    *75       checksum
$--GLL,lll.ll,a,yyyyy.yy,a,hhmmss.ss,A llll.ll = Latitude of position

a = N or S 
yyyyy.yy = Longitude of position 
a = E or W 
hhmmss.ss = UTC of position 
A = status: A = valid data 
"""


def handler_GLL(cmd, *args):
    (
        lat,        # Current latitude
        north_south,  # North/South
        lng,        # Current longitude
        east_west,  # East/West
        utc,        # UTC of position
        status,     # status
        valid_data,  # valid data
    ) = args

    return {
        'lat': (lat, north_south),
        'lng': (lng, east_west),
        'utc': utc,
        'status': status,
        'valid_data': valid_data,
    }


def handler_TXT(cmd, *args):
    #    (
    #    ) = fields

    return {
    }


handlers = {
    'RMC': handler_RMC,  # minimum recommended data
    'VTG': handler_VTG,  # vector track and speed over ground
    'GGA': handler_GGA,  # fix data
    'GSA': handler_GSA,  # overall satellite reception data, missing on some Garmin models
    'GSV': handler_GSV,  # detailed satellite data, missing on some Garmin models
    'GLL': handler_GLL,  # Lat/Lon data - earlier G-12's do not transmit this
    'TXT': handler_TXT,  # ???
}


def process_line(data, line):
    line = line.strip()
    if not line:
        return

    m = LINE_RE.match(line)
    if not m:
        logger.debug('S: [%s]', line)
        return
    ts, cmd, args = m.group(1), m.group(2), m.group(3)
    ts = int(ts)

    # print('A: {0} -> {1}'.format(line, (ts, cmd, args)))
    data.setdefault(ts, {'timestamp': datetime.datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')})

    args, checksum = args.split('*')
    args = args.split(',')

    logger.debug('[%s] %s fields %s len %s', ts, cmd, args, len(args))
    data[ts][cmd] = handlers.get(cmd, handler_dafault)(cmd, *args)


def process_input(src):
    data = {}
    if select.select([sys.stdin, ], [], [], 0.0)[0]:
        logger.debug('process_input: read from stdin')
        with sys.stdin as f:
            for l in f:
                process_line(data, l)
                # print('{0}'.format(line), end='\n')
    else:
        logger.debug('process_input: read from filesystem')
        for root, dirs, files in os.walk(src):
            for filename in files:
                filepath = os.path.join(root, filename)
                if pathlib.Path(filepath).suffix != '.gps':
                    continue
                try:
                    with open(filepath) as f:
                        for l in f:
                            process_line(data, l)
                except Exception as e:
                    logger.debug('%s skipped %s', filepath, e)
            # print(root, "consumes", end=" ")
            # print(sum(os.path.getsize(os.path.join(root, name)) for name in files), end=" ")
            # print("bytes in", len(files), "non-directory files")
            # if 'CVS' in dirs:
            #     dirs.remove('CVS')  # don't visit CVS directories
    return data


def init():
    fullFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(fullFormatter)
    logger.addHandler(sh)

    fh = logging.FileHandler(os.path.join('/tmp', 'blackvue_%s.log' % TS))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fullFormatter)
    logger.addHandler(fh)


def main():
    """
    python merge_gps.py
    python merge_gps.py --src ./ --dst /tmp/out.geojson --debug
    cat *.gps | python merge_gps.py
    """

    parser = argparse.ArgumentParser(description='blackvue tools')

    parser.add_argument('--debug', action='store_true', help='debug mode')
    parser.add_argument('--dry-run', action='store_true', help='dry-run mode')

    parser.add_argument('--src', default='src', help='src path')
    parser.add_argument('--dst', default='dst', help='dst path')

    parser.add_argument('--merge-gps', action='store_true', help='merge gps')

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    if args.dry_run:
        logger.info('DRY RUN mode')
        DRY_RUN = True

    logger.debug(TS)
    logger.debug(args)

    if args.merge_gps:
        input_data = process_input(args.src)
#        print(input_data)
        result = merge_gps(input_data)
        dst = args.dst
    else:
        raise RuntimeError('Unknown mode')


if __name__ == '__main__':
    init()
    main()
