#!/bin/python

import argparse
import datetime
import json
import os
import pathlib
import select
import subprocess
import sys

from time import gmtime, strftime

import nmea

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TS = strftime("%Y%m%d_%H%M%S", gmtime())
DRY_RUN = True


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


def process_gps_input(src):
    nmea_parser = nmea.NMEA()

    if select.select([sys.stdin, ], [], [], 0.0)[0]:
        logger.debug('process_gps_input: read from stdin')
        with sys.stdin as f:
            for nmea_string in f:
                nmea_parser.process_message(nmea_string)
                # print('{0}'.format(line), end='\n')
    else:
        logger.debug('process_gps_input: read from filesystem')
        for root, dirs, files in os.walk(src):
            for filename in files:
                filepath = os.path.join(root, filename)
                if pathlib.Path(filepath).suffix != '.gps':
                    continue
                try:
                    with open(filepath) as f:
                        for nmea_string in f:
                            nmea_parser.process_message(nmea_string)
                except Exception as e:
                    logger.debug('%s skipped %s', filepath, e)
            # print(root, "consumes", end=" ")
            # print(sum(os.path.getsize(os.path.join(root, name)) for name in files), end=" ")
            # print("bytes in", len(files), "non-directory files")
            # if 'CVS' in dirs:
            #     dirs.remove('CVS')  # don't visit CVS directories
    return nmea_parser.get_data()


def merge_gps(source):
    input_data = process_gps_input(source)
#        print(input_data)

    keys = sorted(input_data.keys())
    chunks = {}

    start_ts = keys[0] if len(keys) else None
    last_ts = None

    chunk = {
        '_start': datetime.datetime.fromtimestamp(start_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'points': [],
    }

    for i, ts in enumerate(keys):
        if last_ts and ts - last_ts > 5000:
            chunk['_end'] = datetime.datetime.fromtimestamp(last_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            chunks[(start_ts, last_ts)] = chunk
            chunk = {
                '_start': datetime.datetime.fromtimestamp(start_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'points': [],
            }
            start_ts = ts
        chunk['points'].append(input_data[ts])
        last_ts = ts
    if chunk:
        chunk['_end'] = datetime.datetime.fromtimestamp(last_ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        chunks[(start_ts, last_ts)] = chunk

    for i, ch in enumerate(chunks):
        logger.debug('%s. %s', i, (chunks[ch]['_start'], chunks[ch]['_end']))

    print(json.dumps(chunks[ch], sort_keys=True, indent='  '))


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
        result = merge_gps(args.src)
        dst = args.dst
    else:
        raise RuntimeError('Unknown mode')


if __name__ == '__main__':
    init()
    main()
