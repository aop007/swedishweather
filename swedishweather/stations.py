#!/usr/bin/env python

import json
import pprint
import pickle
import datetime
import logging

import simplekml
import requests
import matplotlib.dates
import matplotlib.pyplot as pyplot
# import sqlalchemy

STATION_FILE_PATH = 'swedishweather/stations.txt'

BOX_NORTH = 68.604977
BOX_WEST = 17.468811

BOX_SOUTH = 67.140676
BOX_EAST = 20.470848

log = logging.getLogger('swedish-weather')

def convert_from_unixtimestamp(timestamp_ms):
    timestamp_s = timestamp_ms / 1000.0

    if timestamp_s < 0:
        date_ref = datetime.datetime.fromtimestamp(0)
        date_target = datetime.datetime.fromtimestamp(-timestamp_s)
        date_delta = date_target - date_ref

        # print(f"date_ref: {date_ref}")
        # print(f"date_delta: {date_delta}")

        date = date_ref - date_delta
    else:
        date = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)
    # end if

    return date

class SwedishStation:
    @classmethod
    def from_dict(cls, station_dict):
        obj = cls()

        obj.__dict__.update(**station_dict)

        obj.from_date = convert_from_unixtimestamp(station_dict['from'])
        obj.to_date = convert_from_unixtimestamp(station_dict['to'])

        return obj
    # end from_dict()

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]
        else:
            raise AttributeError(item)
        # end if
    # end __getattr__()

    # @property
    # def from_date(self):
    #     return datetime.datetime.fromtimestamp(self.__dict__['from'])
    # # end from_date()
    #
    # @property
    # def to_date(self):
    #     return datetime.datetime.fromtimestamp(self.__dict__['to'])
    # # end from_date()

    def __repr__(self):
        return f"Station {self.id} {self.name} {self.latitude} N {self.longitude}"
# end class SwedishStation


class SwedishWeather(object):
    PICKLE_PATH = 'weather_stations.pickle'
    BASE_URL = '/api/version/1.0/parameter/1/station/159880.json'

    def __init__(self):
        self.station_info_dict = {}
        self.station_dict = {}
    # end __init__()

    @property
    def stations_url(self):
        return 'https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/1.json'
    # end stations_url()

    def get_stations_info(self):
        request = requests.get(self.stations_url)

        pprint.pprint(request.__dict__.keys())
        self.station_info_dict = json.loads(request.content)
    # end get_stations_info()

    def save(self):
        with open(self.PICKLE_PATH, 'wb') as f:
            pickle.dump(self, f)
        # end with
    # end save()

    @classmethod
    def from_pickle(cls) -> "SwedishWeather":
        with open(cls.PICKLE_PATH, 'rb') as f:
            sw = pickle.load(f)
            sw.load_stations()
            return sw
        # end with
    # end from_pickle()

    def load_stations(self):
        self.station_dict = {}

        for station_dict in self.station_info_dict['station']:
            station = SwedishStation.from_dict(station_dict)

            self.station_dict[station.id] = station
        # end for
    # end load_stations()

    def export_stations(self):
        kml = simplekml.Kml()

        for station in self.station_dict:
            station_point = kml.newpoint(name=station.name, coords=[(station.longitude, station.latitude, station.height)])
            station_point.altitudemode = simplekml.AltitudeMode.absolute
            station_point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/target.png'

            if station.active:
                station_point.style.iconstyle.color = simplekml.Color.lightgreen
            else:
                station_point.style.iconstyle.color = simplekml.Color.red
            # end if

            station_point.description = pprint.pformat(station.__dict__, indent=True)
        # end for

        kml.savekmz('swedish_stations.kmz')
    # end export_stations()

    def show_timeline(self):
        station_list = []

        for station in self.station_dict.values():   # type: SwedishStation
            if (BOX_WEST <= station.longitude <= BOX_EAST) and (BOX_SOUTH <= station.latitude <= BOX_NORTH):
                station_list.append((
                    station,
                    station.from_date,
                    station.to_date,
                ))
            # end if
        # end for

        station_list = list(sorted(station_list, key=lambda x: x[1], reverse=True))

        fig, ax = pyplot.subplots()

        x_block_list = []
        y_block_list = []

        for ix, (station, from_date, to_date) in enumerate(station_list):
            x_block_list.append([from_date, to_date])
            # y_block_list.append([station.name, station.name])
            y_block_list.append([ix, ix])

            ax.annotate(station.name, (from_date, ix), ha="right")
        # end for

        ax.plot(
            list(zip(*x_block_list)),
            list(zip(*y_block_list)),
            'r', marker='o', mfc='r'
        )

        # ax.set_yticks([station.name for station, _, _ in station_list])

        xfmt = matplotlib.dates.DateFormatter('%Y-%m')
        ax.xaxis.set_major_formatter(xfmt)

        pyplot.show()
    # end show_timeline()
# end SwedishWeather


if __name__ == '__main__':
    sw = SwedishWeather.from_pickle()
    # sw.get_stations_info()
    # sw.save()

    # pprint.pprint(sw.station_info_dict)

    # sw.export_stations()
    sw.show_timeline()
# end if
