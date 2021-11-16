#!/usr/bin/env python

import json
import os.path
import pprint
import pickle
import datetime
import logging

import tabulate
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
# end convert_from_unixtimestamp()


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

    def __repr__(self):
        return f"Station {self.id} {self.name} {self.latitude} N {self.longitude}"
# end class SwedishStation


class SwedishWeather(object):
    PICKLE_PATH = 'weather_stations.pickle'
    BASE_URL = '/api/version/1.0/parameter/1/station/159880.json'

    PARAMETERS = {
        "Min Air Temperature": ("Lufttemperatur", "min, 1 gång per dygn"),
        "Max Air Temperature": ("Lufttemperatur", "max, 1 gång per dygn"),
    }

    def __init__(self):
        self.station_info_dict = {}
        self.station_dict = {}
        self.category_info_dict = {}
        self.categories = {}
    # end __init__()

    @property
    def stations_url(self):
        return 'https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/1.json'
    # end stations_url()

    @property
    def category_url(self):
        return "https://opendata-download-metobs.smhi.se/api/version/latest.json"
    # end category_url()

    def get_stations_info(self):
        request = requests.get(self.stations_url)
        self.station_info_dict = json.loads(request.content)
    # end get_stations_info()

    def get_category_info(self, show=False):
        request = requests.get(self.category_url)
        self.category_info_dict = json.loads(request.content)

        if show:
            pprint.pprint(self.category_info_dict)
            print(list(self.category_info_dict.keys()))
        # end if

        output = []

        for ressource_dict in self.category_info_dict.get('resource'):
            # print(ressource_dict.get('title'), ressource_dict.get('summary'), ressource_dict.get('link'))

            title = ressource_dict.get('title')
            summary = ressource_dict.get('summary')
            key = ressource_dict.get('key')

            output.append((
                title,
                summary,
                key,
            ))

            if title == 'Lufttemperatur' and '1 gång per dygn' in summary:
                self.categories[f"{title} {summary}"] = key
            # end if
        # end for

        if show:
            print()
            print(tabulate.tabulate(output))

            print()
            pprint.pprint(self.categories)
        # end if
    # end get_category_info()

    def save(self):
        with open(self.PICKLE_PATH, 'wb') as f:
            pickle.dump(self, f)
        # end with
    # end save()

    @classmethod
    def from_pickle(cls) -> "SwedishWeather":
        if os.path.exists(cls.PICKLE_PATH):
            with open(cls.PICKLE_PATH, 'rb') as f:
                log.critical(f"From pickle")
                sw = pickle.load(f)
            # end with
        else:
            sw = cls()
            sw.get_stations_info()
            sw.load_stations()
            sw.get_category_info()
        # end if

        return sw
    # end from_pickle()

    def load_stations(self):
        self.station_dict = {}

        for station_dict in self.station_info_dict['station']:
            station = SwedishStation.from_dict(station_dict)

            self.station_dict[station.id] = station
        # end for
    # end load_stations()

    def get_scoped_stations(self):
        for station in self.station_dict.values():
            if (BOX_WEST <= station.longitude <= BOX_EAST) and (BOX_SOUTH <= station.latitude <= BOX_NORTH):
                yield station
            # end if
        # end for
    # end get_scoped_stations()

    def export_stations(self):
        kml = simplekml.Kml()

        for station in self.station_dict.values():
            if (BOX_WEST <= station.longitude <= BOX_EAST) and (BOX_SOUTH <= station.latitude <= BOX_NORTH):

                station_point = kml.newpoint(name=station.name, coords=[(station.longitude, station.latitude, station.height)])
                station_point.altitudemode = simplekml.AltitudeMode.absolute
                station_point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/target.png'

                if station.active:
                    station_point.style.iconstyle.color = simplekml.Color.lightgreen
                else:
                    station_point.style.iconstyle.color = simplekml.Color.red
                # end if

                station_point.description = pprint.pformat(station.__dict__, indent=True)
            # end if
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

            ax.annotate(station.name, (from_date, ix), ha="right", va='center')
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

    def air_temperature_url(self, station_id: int, min_max='min'):
        try:
            key = self.categories[f'Lufttemperatur {min_max}, 1 gång per dygn']
        except KeyError:
            log.error(f"self.categories: {list(self.categories.keys())}")
            raise
        # end try

        # return f"https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/{key}/station/{station_id}/period.json"
        return f"https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/{key}/station/{station_id}/period/corrected-archive.json"
    # end air_temperature_url()

    def collect_temperature(self, years_back=30.0):
        for station in self.get_scoped_stations():  # type: SwedishStation
            print(station)

            url_min = self.air_temperature_url(station.id, 'min')
            # log.critical(f"url_min: {url_min}")

            response = requests.get(
                url_min,
                headers={'Content-type': 'application/json'}
            )

            temperature_data = json.loads(response.content)

            csv_links = temperature_data.get('data')

            for csv_link in csv_links:
                # print()
                # pprint.pprint(csv_link)

                for link in csv_link.get('link'):
                    csv_url = link.get('href')

                    print(f"csv_url: {csv_url}")
                # end for
            # end for

            break
        # end for
    # end collect_temperature()
# end SwedishWeather


if __name__ == '__main__':
    sw = SwedishWeather.from_pickle()
    # sw.get_category_info()
    # sw.show_category_info()
    # sw.get_stations_info()
    # sw.save()

    # pprint.pprint(sw.station_info_dict)

    # sw.export_stations()
    # sw.show_timeline()

    sw.get_category_info(show=False)
    sw.collect_temperature()
    sw.save()
# end if
