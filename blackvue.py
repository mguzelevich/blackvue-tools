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

import geojson
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


def process_input(args):
    src = args.get('src')

    nmea_parser = nmea.NMEA()

    input_files = []

    if select.select([sys.stdin, ], [], [], 0.0)[0]:
        logger.debug('process_input: read from stdin')
        # locale.getpreferredencoding(do_setlocale=True)
        # locale.setlocale(locale.LC_ALL, '')
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="latin-1")
        input_files.append('<STDIN>')
    else:
        logger.debug('process_input: read from filesystem')
        for root, dirs, files in os.walk(src):
            for filename in files:
                filepath = os.path.join(root, filename)
                if pathlib.Path(filepath).suffix != '.gps':
                    continue
                logger.debug('process_input: add file [%s]', filepath)
                input_files.append(filepath)

    nmea_records = {}
    for i, filepath in enumerate(input_files):
        logger.info('process_input: file [%s]', filepath)
        try:
            with sys.stdin if filepath == '<STDIN>' else open(filepath, encoding="latin-1") as f:
                idx = 0
                for nmea_string in f:
                    idx += 1
                    try:
                        ts, msg = nmea_parser.process_message(nmea_string)

                        nmea_records.setdefault(ts, {'timestamp': ts})
                        nmea_records[ts].update(msg)
                    except nmea.ProcessMessageSkippedLineException as e:
                        pass  # raise e
                    except nmea.ProcessMessageException as e:
                        logger.warning(e.log(idx))
        except Exception as e:
            logger.error('process_input: file [%s] skipped with error [%s]', filepath, e)
            raise e

    result = []
    for r in sorted(nmea_records.keys()):
        result.append(nmea_records[r])

    return result


def split_tracks(nmea_data):
    if not len(nmea_data):
        return []

    chunks = []
    idx = -1

    last_ts = None
    for i, record in enumerate(nmea_data):
        ts = record.get('timestamp')
        if not last_ts or ts - last_ts > 5000:
            chunks.append([])
            idx += 1
            logger.debug('chunk %s created. record=%s. ts=%s', idx, i, ts_short(ts))
        last_ts = ts
        chunks[idx].append(record)

    return chunks


def out_nmea(args, series):
    if len(series) == 1:
        chunk = series[0]
        out = {
            '_ts': [ts_str(chunk[0]['timestamp']), ts_str(chunk[-1]['timestamp'])],
            'records': chunk
        }
        sys.stdout.write(json.dumps(out, sort_keys=True, indent='  '))
    else:
        for i, chunk in enumerate(series):
            ts_start, ts_end = chunk[0]['timestamp'], chunk[-1]['timestamp']
            ts_start_str, ts_end_str = ts_str(ts_start), ts_str(ts_end)
            out = {
                '_ts': [ts_start_str, ts_end_str],
                'records': chunk
            }
            logger.debug('%s. %s', i, (ts_start_str, ts_end_str))

            filename = 'track_{0}_{1}.nmea'.format(ts_short(ts_start), ts_short(ts_end))
            filepath = os.path.join(args.get('dst-dir', './'), filename)
            with open(filepath, mode='w+') as f:
                f.write(json.dumps(out, sort_keys=True, indent='  '))


def out_geojson(args, series):
    if len(series) == 1:
        gj = geojson.GeoJsonFeatureCollection()
        for i, r in enumerate(series[0]):
            ll = [r.get('RMC_lng'), r.get('RMC_lat')]
            if ll[0] and ll[1]:
                gj.add_point(ll)
        sys.stdout.write(gj.dump())
    else:
        gj = geojson.GeoJsonFeatureCollection()
        for i, s in enumerate(series):
            gj_ls = geojson.LineString()
            for item in s:
                ll = [item.get('RMC_lng'), item.get('RMC_lat')]
                if ll[0] and ll[1]:
                    gj_ls.add_point(ll)
            gj.add_feature(gj_ls)
        sys.stdout.write(gj.dump())


def process_gps(args):
    nmea_data = process_input(args)
#        print(nmea_data)

    series = [
        nmea_data
    ]

    if args.get('split-files') or args.get('split-tracks'):
        series = split_tracks(nmea_data)

    if args.get('nmea'):
        out_nmea(args, series)
    elif args.get('geojson'):
        out_geojson(args, series)

    # for i, ch in enumerate(chunks):
    #     chunk = chunks[ch]
    #     ts_start, ts_end = ch
    #     ts_str_start, ts_str_end = chunk['_start'], chunk['_end']

    #     logger.debug('%s. %s', i, (ts_str_start, ts_str_end))

    #     filepath = os.path.join(dst, 'track_{0}_{1}.nmea'.format(ts_short(ts_start), ts_short(ts_end)))
    #     with open(filepath, mode='w+') as f:
    #         f.write(json.dumps(chunk, sort_keys=True, indent='  '))

    #     filepath = os.path.join(dst, 'track_{0}_{1}.geojson'.format(ts_short(ts_start), ts_short(ts_end)))
    #     with open(filepath, mode='w+') as f:
    #         gj = geojson.GeoJson()
    #         for i, p in enumerate(chunk['points']):
    #             ll = [p.get('RMC_lng'), p.get('RMC_lat')]
    #             if ll[0] and ll[1]:
    #                 gj.add_point(ll)
    #         f.write(gj.dump())


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
    geojson.logger = logger


def main():
    """
    python blackvue.py
    python blackvue.py --src ./ --dst /tmp/out.geojson --debug
    cat *.gps | python blackvue.py
    """

    parser = argparse.ArgumentParser(description='blackvue tools')

    parser.add_argument('--debug', action='store_true', help='debug mode')
    parser.add_argument('--dry-run', action='store_true', help='dry-run mode')

    # process-gps
    parser.add_argument('--process-gps', action='store_true', help='process *.gps files')
    parser.add_argument('--nmea', action='store_true', help='save nmea files')
    parser.add_argument('--geojson', action='store_true', help='save geojson files')
    parser.add_argument('--split-files', action='store_true', help='split output by rides')
    parser.add_argument('--split-tracks', action='store_true', help='split tracks in one geojson file')

    parser.add_argument('--src-dir', default=None, help='src path')
    parser.add_argument('--dst-dir', default=None, help='dst path')
    parser.add_argument('--dst-file', default=None, help='dst path')

    args = parser.parse_args()

    global_args = {
        'debug': args.debug,
        'dry-run': args.dry_run,
        'nmea': args.nmea,
        'geojson': args.geojson,
        'split-files': args.split_files,
        'split-tracks': args.split_tracks,
        'src-dir': args.src_dir,
        'dst-dir': args.dst_dir,
        'dst-file': args.dst_file,
    }

    if global_args.get('debug'):
        logger.setLevel(logging.DEBUG)
    if global_args.get('dry-run'):
        logger.info('DRY RUN mode')

    logger.info('ARGS: %s, TS: %s', global_args, TS)

    if not global_args.get('nmea') and not global_args.get('geojson'):
        raise RuntimeError('USAGE: --process-gps AND (--nmea AND/OR --geojson)')

    if global_args.get('nmea') and global_args.get('geojson'):
        if global_args.get('dst-file') or not global_args.get('dst-dir'):
            raise RuntimeError('USAGE: (--nmea AND --geojson) AND --dst-dir AND NOT --dst-file')

    if global_args.get('split-files'):
        if global_args.get('dst-file') or not global_args.get('dst-dir'):
            raise RuntimeError('USAGE: --split-files AND --dst-dir AND NOT --dst-file')

    if args.process_gps:
        process_gps(global_args)
    else:
        raise RuntimeError('Unknown mode')


if __name__ == '__main__':
    init()
    main()
