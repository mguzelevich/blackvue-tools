#!/bin/python

import json

import logging
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# "type":"Feature",
# "type":"FeatureCollection",
# "type":"Geometry",


tmpl = """
{
  "type":"FeatureCollection",
  "features":[
    {
      "type":"Feature",
      "geometry":{"type":"Point","coordinates":[102,0.5]},
      "properties":{"prop0":"value0"}
    },
    {
      "type":"Feature",
      "geometry":{"type":"LineString","coordinates":[[102,0],[103,1],[104,0],[105,1]]},
      "properties":{"prop0":"value0","prop1":0}
    },
    {
      "type":"Feature",
      "geometry":{"type":"Polygon","coordinates":[[[100,0],[101,0],[101,1],[100,1],[100,0]]]},
      "properties":{"prop0":"value0","prop1":{"this":"that"}}
    }
  ]
}
"""

tmpl = """
{
  "type":"FeatureCollection",
  "features":[
    {
      "type":"Feature",
      "geometry":{"type":"LineString","coordinates":[[102,0],[103,1],[104,0],[105,1]]},
      "properties":{"prop0":"value0","prop1":0}
    }
  ]
}
"""


class GeoJson(object):

    def __init__(self):
        self.data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": []
                    },
                    "properties":{
                        "prop0": "value0", "prop1": 0
                    }
                }
            ]
        }

    def add_point(self, point):
        # lat, lon = point
        # logger.debug('add %s', point)
        self.data['features'][0]['geometry']['coordinates'].append(point)

    def dump(self):
        return json.dumps(self.data, sort_keys=True, indent='  ')
