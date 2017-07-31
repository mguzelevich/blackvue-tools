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
      "properties":{"stroke":"red"}
    }
  ]
}
"""


class LineString(object):

    def __init__(self):
        self.coordinates = []

    def add_point(self, point):
        # lat, lon = point
        # logger.debug('add %s', point)
        self.coordinates.append(point)

    def data(self):
        tmpl = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": []
            },
            "properties": {}
        }
        for p in self.coordinates:
            if p:
                tmpl['geometry']['coordinates'].append(p)
        return tmpl

    def dump(self):
        return self.data


class GeoJsonFeatureCollection(object):

    def __init__(self):
        self.features = []

    def add_feature(self, feature):
        # lat, lon = point
        # logger.debug('add %s', point)
        self.features.append(feature)

    def data(self):
        tmpl = {
            "type": "FeatureCollection",
            "features": []
        }
        for f in self.features:
            if f.coordinates:
                tmpl['features'].append(f.data())
        return tmpl

    def dump(self):
        return json.dumps(self.data(), sort_keys=True, indent='  ')


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
                    "properties": {"stroke": "red"}
                }
            ]
        }

    def add_point(self, point):
        # lat, lon = point
        # logger.debug('add %s', point)
        self.data['features'][0]['geometry']['coordinates'].append(point)

    def dump(self):
        return json.dumps(self.data, sort_keys=True, indent='  ')
