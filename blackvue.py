#!/bin/python

import argparse
import datetime
import json
import io
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

TS_ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
TS_SHORT_FORMAT = '%Y%m%d_%H%M%S'

TS = strftime("%Y%m%d_%H%M%S", gmtime())
DRY_RUN = True


def ts_str(ts):
    return datetime.datetime.fromtimestamp(ts / 1000.0).strftime(TS_ISO_FORMAT)


def ts_short(ts):
    return datetime.datetime.fromtimestamp(ts / 1000.0).strftime(TS_SHORT_FORMAT)


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

    input_files = []

    if select.select([sys.stdin, ], [], [], 0.0)[0]:
        logger.debug('process_gps_input: read from stdin')
        # locale.getpreferredencoding(do_setlocale=True)
        # locale.setlocale(locale.LC_ALL, '')
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="latin-1")
        input_files.append('<STDIN>')
    else:
        logger.debug('process_gps_input: read from filesystem')
        for root, dirs, files in os.walk(src):
            for filename in files:
                filepath = os.path.join(root, filename)
                if pathlib.Path(filepath).suffix != '.gps':
                    continue
                logger.debug('process_gps_input: add file [%s]', filepath)
                input_files.append(filepath)

    data = {}

    for i, filepath in enumerate(input_files):
        logger.info('process_gps_input: file [%s]', filepath)
        try:
            with sys.stdin if filepath == '<STDIN>' else open(filepath, encoding="latin-1") as f:
                idx = 0
                for nmea_string in f:
                    idx += 1
                    try:
                        ts, msg = nmea_parser.process_message(nmea_string)

                        data.setdefault(ts, {'timestamp': ts_str(ts)})
                        data[ts].update(msg)
                    except nmea.IncorrectLine as e:
                        logger.warning('[L%s] %s', idx, e)
                    except nmea.SkippedLine as e:
                        pass  # raise e
        except Exception as e:
            logger.error('process_gps_input: file [%s] skipped with error [%s]', filepath, e)

    return data


def merge_gps(source, dst):
    nmea_data = process_gps_input(source)
#        print(nmea_data)

    keys = sorted(nmea_data.keys())
    chunks = {}

    start_ts = keys[0] if len(keys) else None
    last_ts = None

    chunk = {
        '_start': ts_str(start_ts),
        'points': [],
    }

    for i, ts in enumerate(keys):
        if last_ts and ts - last_ts > 5000:
            chunk['_end'] = ts_str(last_ts)
            chunks[(start_ts, last_ts)] = chunk
            chunk = {
                '_start': ts_str(start_ts),
                'points': [],
            }
            start_ts = ts
        chunk['points'].append(nmea_data[ts])
        last_ts = ts
    if chunk:
        chunk['_end'] = ts_str(last_ts)
        chunks[(start_ts, last_ts)] = chunk

    for i, ch in enumerate(chunks):
        chunk = chunks[ch]
        ts_start, ts_end = ch
        ts_str_start, ts_str_end = chunk['_start'], chunk['_end']

        logger.debug('%s. %s', i, (ts_str_start, ts_str_end))

        filepath = os.path.join(dst, 'track_{0}_{1}.nmea'.format(ts_short(ts_start), ts_short(ts_end)))
        with open(filepath, mode='w+') as f:
            f.write(json.dumps(chunk, sort_keys=True, indent='  '))

        filepath = os.path.join(dst, 'track_{0}_{1}.geojson'.format(ts_short(ts_start), ts_short(ts_end)))
        with open(filepath, mode='w+') as f:
            geojson = {}
            for i, p in chunk['points']:
                pass


def init():
    fullFormatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # fullFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(fullFormatter)
    logger.addHandler(sh)

    fh = logging.FileHandler(os.path.join('/tmp', 'blackvue_%s.log' % TS))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fullFormatter)
    logger.addHandler(fh)

    nmea.logger = logger


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
        result = merge_gps(args.src, args.dst)
    else:
        raise RuntimeError('Unknown mode')


if __name__ == '__main__':
    init()
    main()
