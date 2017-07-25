#!/bin/python

import datetime
import re

import logging
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)


# [1500310610235]$GPGLL,5355.68249,N,02738.67852,E,135648.00,A,A*63
LINE_RE_STRING = r'\[([0-9]+)\]\$GP([A-Z]+),(.+)'
LINE_RE = re.compile(LINE_RE_STRING)


def lat(nmea_lat, north_south):
    lat_value = 0.0
    try:
        lat_value = float(nmea_lat) / 100.0
    except Exception as e:
        raise RuntimeError(nmea_lat, e)
    return lat_value


def lng(nmea_lng, east_west):
    lng_value = 0.0
    try:
        lng_value = float(nmea_lng) / 100.0
    except Exception as e:
        raise RuntimeError(nmea_lng, e)
    return lng_value


def nmea_datetime(fix_date, fix_time):
    # "RMC_date": "090717",
    # "RMC_fix_time": "055554.00",
    dt = datetime.datetime.strptime(' '.join((fix_date, fix_time, )), '%d%m%y %H%M%S.%f')
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


class SkippedLine(Exception):
    pass


class IncorrectLine(Exception):
    pass


class NMEA(object):

    def __init__(self):
        self.handlers = {
            'RMC': self.handler_RMC,  # minimum recommended data
            'VTG': self.handler_VTG,  # vector track and speed over ground
            'GGA': self.handler_GGA,  # fix data
            'GSA': self.handler_GSA,  # overall satellite reception data, missing on some Garmin models
            'GSV': self.handler_GSV,  # detailed satellite data, missing on some Garmin models
            'GLL': self.handler_GLL,  # Lat/Lon data - earlier G-12's do not transmit this
            'TXT': self.handler_TXT,  # ???
        }

        self.data = {}

    def get_data(self):
        return self.data

    def process_message(self, nmea_string):
        nmea_string = nmea_string.strip()
        if not nmea_string:
            raise SkippedLine()

        m = LINE_RE.match(nmea_string)
        if not m:
            raise IncorrectLine(repr(nmea_string))

        ts, cmd, args = m.group(1), m.group(2), m.group(3)
        ts = int(ts)

        # print('A: {0} -> {1}'.format(line, (ts, cmd, args)))
        args, checksum = args.split('*')
        args = args.split(',')

        logger.debug('[%s] %s fields %s len %s', ts, cmd, args, len(args))

        self.data.setdefault(ts, {'timestamp': datetime.datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')})
        self.data[ts].update(self.handlers.get(cmd, self.handler_dafault)(cmd, *args))

    def handler_dafault(self, cmd, *args):
        logger.warning('unknown command [%s] %s', cmd, args)

    def handler_RMC(self, cmd, *args):
        """
        Message Structure:
        $GPRMC,hhmmss,status,latitude,N,longitude,E,spd,cog,ddmmyy,mv,mvE,mode*cs<CR><LF>

        Example:
        $GPRMC,083559.00,A,4717.11437,N,00833.91522,E,0.004,77.52,091202,,,A*57

        No. Example     Format      Name        Unit    Description
        0   $GPRMC      string      $GPRMC      -       Message ID, RMC protocol header
        1   083559.00   hhmmss.sss  hhmmss.ss   -       UTC Time, Time of position fix
        2   A           character   status      -       Status, V = Navigation receiver warning,
                                                                A = Data valid, see Position Fix Flags description
        3   4717.11437  ddmm.mmmm   Latitude    -       Latitude, Degrees + minutes, see Format description
        4   N           character   N           -       N/S Indicator, hemisphere N=north or S=south
        5   00833.91522 dddmm.mmmm  Longitude   -       Longitude, Degrees + minutes, see Format description
        6   E           character   E           -       E/W indicator, E=east or W=west
        7   0.004       numeric     Spd         knots   Speed over ground
        8   77.52       numeric     Cog         degrees Course over ground
        9   091202      ddmmyy      date        -       Date in day, month, year format
        10  -           numeric     mv          degrees Magnetic variation value, not being output by receiver
        11  -           character   mvE         -       Magnetic variation E/W indicator, not being output by receiver
        12  -           character   mode        -       Mode Indicator, see Position Fix Flags description
        13  *57         hexadecimal cs          -       Checksum
        """
        (
            hhmmss,           # Fix taken at 12:35:19 UTC
            status,             # Status A=active or V=Void.
            latitude,           # Latitude 48 deg 07.038' N
            ns,        # North/South
            longitude,           # Longitude 11 deg 31.000' E
            ew,          # East/West
            spd,              # Speed over the ground in knots
            angle,              # Track angle in degrees True
            date,           # Date - 23rd of March 1994
            mv,  # Magnetic Variation
            mvE,  # Magnetic Variation (E/W)
            mode,  # Mode
        ) = args

        if status != 'A':
            return {
                'RMC_status': status,
            }

        return {
            'RMC_fix_datetime': nmea_datetime(date, hhmmss),
            'RMC_status': status,
            'RMC_lat': lat(latitude, ns),
            'RMC_lng': lng(longitude, ew),
            'RMC_speed': spd,
            'RMC_angle': angle,
            'RMC_magnetic_variation': ' '.join((mv, mvE))
        }

    def handler_VTG(self, cmd, *args):
        """
        Message Structure:
        $GPVTG,cogt,T,cogm,M,sog,N,kph,K,mode*cs<CR><LF>

        Example:
        $GPVTG,77.52,T,,M,0.004,N,0.008,K,A*06

        No. Example Format      Name    Unit    Description
        0   $GPVTG  string      $GPVTG  -       Message ID, VTG protocol header
        1   77.52   numeric     cogt    degrees Course over ground (true)
        2   T       character   T       -       Fixed field: true
        3   -       numeric     cogm    degrees Course over ground (magnetic), not output
        4   M       character   M       -       Fixed field: magnetic
        5   0.004   numeric     sog     knots   Speed over ground
        6   N       character   N       -       Fixed field: knots
        7   0.008   numeric     kph     km/h    Speed over ground
        8   K       character   K       -       Fixed field: kilometers per hour
        9   A       character   mode    -       Mode Indicator, see Position Fix Flags description
        10  *06     hexadecimal cs      -       Checksum
        """
        (
            cogt,
            true,
            cogm,
            magnetic,
            sog,
            knots,
            kph,
            kmh,
            mode
        ) = args

        if mode != 'A':
            return {
                'VTG_mode': mode,
            }

        if true != 'T':
            logger.debug('true != T %s', args)
            raise RuntimeError('true != T')
        if magnetic != 'M':
            logger.debug('magnetic != M %s', args)
            raise RuntimeError('magnetic != M')
        if knots != 'N':
            logger.debug('knots != N %s', args)
            raise RuntimeError('knots != N')
        if kmh != 'K':
            logger.debug('kmh != K %s', args)
            raise RuntimeError('kmh != K')

        return {
            'VTG_cogt': cogt,
            'VTG_cogt': cogm,
            'VTG_sog': sog,
            'VTG_kph': kph,
            'VTG_mode': mode,
        }

    def handler_GGA(self, cmd, *args):
        """
        Message Structure:
        $GPGGA,hhmmss.ss,Latitude,N,Longitude,E,FS,NoSV,HDOP,msl,m,Altref,m,DiffAge,DiffStation*cs<CR><LF>

        Example:
        $GPGGA,092725.00,4717.11399,N,00833.91590,E,1,8,1.01,499.6,M,48.0,M,,0*5B

        No. Example     Format      Name        Unit    Description
        0   $GPGGA      string      $GPGGA      -       Message ID, GGA protocol header
        1   092725.00   hhmmss.sss  hhmmss.ss   -       UTC Time, Current time
        2   4717.11399  ddmm.mmmm   Latitude    -       Latitude, Degrees + minutes, see Format description
        3   N           character   N           -       N/S Indicator, N=north or S=south
        4   00833.91590 dddmm.mmmm  Longitude   -       Longitude, Degrees + minutes, see Format description
        5   E           character   E           -       E/W indicator, E=east or W=west
        6   1           digit       FS          -       Position Fix Status Indicator, See Table below and Position Fix Flags description
        7   8           numeric     NoSV        -       Satellites Used, Range 0 to 12
        8   1.01        numeric     HDOP        -       HDOP, Horizontal Dilution of Precision
        9   499.6       numeric     msl         m       MSL Altitude
        10  M           character   uMsl        -       Units, Meters (fixed field)
        11  48.0        numeric     Altref      m       Geoid Separation
        12  M           character   uSep        -       Units, Meters (fixed field)
        13  -           numeric     DiffAge     s       Age of Differential Corrections, Blank (Null) fields when DGPS is not used
        14  0           numeric     DiffStation -       Diff. Reference Station ID
        """
        #    (
        #    ) = args

        return {
        }

    def handler_GSA(self, cmd, *args):
        """
        Message Structure:
        $GPGSA,Smode,FS{,sv},PDOP,HDOP,VDOP*cs<CR><LF>

        Example:
        $GPGSA,A,3,23,29,07,08,09,18,26,28,,,,,1.94,1.18,1.54*0D

        No.     Example     Format      Name    Unit    Description
        0       $GPGSA      string      $GPGSA  -       Message ID, GSA protocol header
        1       A           character   Smode   -       Smode, see first table below
        2       3           digit       FS      -       Fix status, see second table below and Position Fix Flags description

        Start of repeated block (12 times)
        3+1*N   29         numeric      sv      -       Satellite number
        End of repeated block

        15      1.94        numeric     PDOP    -       Position dilution of precision
        16      1.18        numeric     HDOP    -       Horizontal dilution of precision
        17      1.54        numeric     VDOP    -       Vertical dilution of precision
        18      *0D         hexadecimal cs      -       Checksum
        """
        #    (
        #    ) = args

        return {
        }

    def handler_GSV(self, cmd, *args):
        """
        Message Structure:
        $GPGSV,NoMsg,MsgNo,NoSv,{,sv,elv,az,cno}*cs<CR><LF>

        Example:
        $GPGSV,3,1,10,23,38,230,44,29,71,156,47,07,29,116,41,08,09,081,36*7F
        $GPGSV,3,2,10,10,07,189,,05,05,220,,09,34,274,42,18,25,309,44*72
        $GPGSV,3,3,10,26,82,187,47,28,43,056,46*77

        No.     Example     Format      Name    Unit    Description
        0       $GPGSV      string      $GPGSV  -       Message ID, GSV protocol header
        1       3           digit       NoMsg   -       Number of messages, total number of GPGSV messages being output
        2       1           digit       MsgNo   -       Number of this message
        3       10          numeric     NoSv    -       Satellites in View

        Start of repeated block (1..4 times)
        4+4*N   23          numeric     sv      -       Satellite ID
        5+4*N   38          numeric     elv     degrees Elevation, range 0..90
        6+4*N   230         numeric     az      degrees Azimuth, range 0..359
        7+4*N   44          numeric     cno     dBHz    C/N0, range 0..99, null when not tracking
        End of repeated block

        5..16 *7F       hexadecimal cs - Checksum
        """
        #    (
        #    ) = args

        return {
        }

    def handler_GLL(self, cmd, *args):
        """
        Message Structure:
        $GPGLL,Latitude,N,Longitude,E,hhmmss.ss,Valid,Mode*cs<CR><LF>

        Example:
        $GPGLL,4717.11364,N,00833.91565,E,092321.00,A,A*60

        No. Example     Format      Name        Unit    Description
        0   $GPGLL      string      $GPGLL      -       Message ID, GLL protocol header
        1   4717.11364  ddmm.mmmm   Latitude    -       Latitude, Degrees + minutes, see Format description
        2   N           character   N           -       N/S Indicator, hemisphere N=north or S=south
        3   00833.91565 dddmm.mmmm  Longitude   -       Longitude, Degrees + minutes, see Format description
        4   E           character   E           -       E/W indicator, E=east or W=west
        5   092321.00   hhmmss.sss  hhmmss.ss   -       UTC Time, Current time
        6   A           character   Valid       -       V = Data invalid or receiver warning, A = Data valid. See Position Fix Flags description Start of optional block
        7   A           character   Mode        -       Positioning Mode, see Position Fix Flags description End of optional block
        7   *60         hexadecimal cs          -       Checksum
        """
        (
            latitude,        # Current latitude
            ns,  # North/South
            longitude,        # Current longitude
            ew,  # East/West
            utc,        # UTC of position
            valid,     # status
            mode,  # valid data
        ) = args

        if valid != 'A':
            return {
                'GLL_valid': valid,
                'GLL_mode': mode,
            }

        return {
            'GLL_lat': lat(latitude, ns),
            'GLL_lng': lng(longitude, ew),
            'GLL_utc': utc,
            'GLL_valid': valid,
            'GLL_mode': mode,
        }

    def handler_TXT(self, cmd, *args):
        """
        Message Structure:
        $GPTXT,xx,yy,zz,ascii data*cs<CR><LF>

        Example:
        $GPTXT,01,01,02,u-blox ag - www.u-blox.com*50
        $GPTXT,01,01,02,ANTARIS ATR0620 HW 00000040*67

        No. Example         Format          Name    Unit    Description
        0   $GPTXT          string          $GPTXT  -       Message ID, TXT protocol header
        1   01              numeric         xx      -       Total number of messages in this transmission, 01..99
        2   01              numeric         yy      -       Message number in this transmission, range 01..xx
        3   02              numeric         zz      -       Text identifier, u-blox GPS receivers specify the severity of the message with this number.
                                                            - 00 = ERROR
                                                            - 01 = WARNING
                                                            - 02 = NOTICE
                                                            - 07 = USER
        4   www.u-blox.com  string          string  -       Any ASCII text
        5   *67             hexadecimal     cs - Checksum
        """
        #    (
        #    ) = fields

        return {
        }
