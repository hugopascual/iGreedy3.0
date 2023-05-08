#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
# external modules imports
import requests
import geocoder
import random
import time
# internal modules imports
from utils.constants import (
    RIPE_ATLAS_MEASUREMENTS_BASE_URL,
    RIPE_ATLAS_PROBES_BASE_URL,
    KEY_FILEPATH,
    HUNTER_MEASUREMENTS_PATH,
    SPEED_OF_LIGHT,
    FIBER_RI
)
from utils.common_functions import (
    json_file_to_dict,
    dict_to_json_file,
    check_discs_intersect,
    distance
)


class Hunter:
    def __init__(self, target: str, origin: (float, float) = ()):
        self._target = target
        # origin format = (latitude, longitude)
        if origin != ():
            self._origin = origin
        else:
            latlng = geocoder.ip("me").latlng
            self._origin = (latlng[0], latlng[1])

        self._radius = 20
        self._url = RIPE_ATLAS_MEASUREMENTS_BASE_URL + "/?key={}".format(
            self.get_ripe_key()
        )
        self._measurement_id = 0
        self._measurement_result_filepath = "hunter_measurement.json"
        self._results_measurements = {"traceroute": {}, "pings": {}}

    def hunt(self):
        self.traceroute_measurement()
        self.build_measurement_filepath()
        # Geolocate last valid hop in traceroute measurement
        last_hop_geo = self.geolocate_last_hop()
        print("Last Hop location: ", last_hop_geo)
        self._results_measurements["last_hop"] ={"geolocation": last_hop_geo}
        # Pings from near last hop geo
        self.obtain_pings_near_last_hop(last_hop_geo)
        # Intersection of discs from pings
        if self.check_ping_discs_intersection():
            print("All pings generated discs intersect")
            # Location of airports inside intersection
            self.check_airports_inside_intersection()
        else:
            print("Some pings do not intersect. Bad scenario")
        self.save_measurements()

    def traceroute_measurement(self):
        print("###########")
        print("Traceroute phase initiated")
        print("###########")
        # Make traceroute from origin
        probe_id = self.find_probes_in_circle(
            latitude=self._origin[0],
            longitude=self._origin[1],
            radius=self._radius,
            num_probes=1
        )
        traceroute_data = {
            "definitions": [
                {
                    "target": self._target,
                    "description": "Hunter traceroute %s" % self._target,
                    "type": "traceroute",
                    "is_oneoff": True,
                    "af": 4,
                    "protocol": "ICMP",
                    "packets": 3
                }
            ],
            "probes": [
                {
                    "requested": 1,
                    "type": "probes",
                    "value": ",".join(map(str, probe_id))
                }
            ]
        }
        self.make_ripe_measurement(data=traceroute_data)
        if self._measurement_id == 0:
            print("Measure could not start")
            return
        else:
            print("Measure ID: ", self._measurement_id)
        # Obtain results
        self._results_measurements["traceroute"] = \
            self.get_measurement_results()

    def make_ripe_measurement(self, data: dict):
        # Start the measurement and get measurement id
        response = {}
        try:
            response = requests.post(self._url, json=data).json()
            self._measurement_id = response["measurements"][0]
        except Exception as e:
            print(e.__str__())
            print(response)

    def get_probes_scheduled(self) -> int:
        probes_scheduled_url = RIPE_ATLAS_MEASUREMENTS_BASE_URL + \
                               "{}/?fields=probes_scheduled".format(
                                   self._measurement_id)
        retrieved = False
        while not retrieved:
            time.sleep(1)
            try:
                response = requests.get(probes_scheduled_url).json()
                return int(response["probes_scheduled"])
            except:
                print("Measure not scheduled yet")

    def build_measurement_filepath(self):
        filename = "{}_{}_{}_{}.json".format(
            self._target,
            self._origin[0], self._origin[1],
            self._measurement_id)
        self._measurement_result_filepath = HUNTER_MEASUREMENTS_PATH + filename

    def get_measurement_results(self) -> dict:
        results_measurement_url = \
            RIPE_ATLAS_MEASUREMENTS_BASE_URL + "{}/results".format(
                self._measurement_id
            )
        delay = 5
        enough_results = False
        attempts = 0
        response = {}

        while not enough_results:
            probes_scheduled = self.get_probes_scheduled()
            print("Total probes scheduled for measurement: ", probes_scheduled)
            print("Wait {} seconds for results. Number of attempts {}".
                  format(delay, attempts))
            time.sleep(delay)
            delay = 15
            attempts += 1
            response = requests.get(results_measurement_url).json()
            print("Obtained response from {} probes".format(len(response)))
            if len(response) == probes_scheduled:
                print("Results retrieved")
                enough_results = True
            elif attempts >= 10:
                enough_results = True
            else:
                enough_results = False
        return response

    def geolocate_last_hop(self) -> dict:
        last_hop = self.select_last_hop_valid()
        last_hop_direction = last_hop["result"][0]["from"]
        print("Last Hop IP direction: ", last_hop_direction)
        min_rtt = min(result["rtt"] for result in last_hop["result"])
        print("For {} direction min rtt is {} ms".format(
            last_hop_direction, min_rtt)
        )
        # TODO geolocate last_hop_direction better
        last_hop_geo = self.geolocate_ip_commercial_database(
            ip=last_hop_direction)
        return last_hop_geo

    def select_last_hop_valid(self) -> dict:
        measurement_data = self._results_measurements["traceroute"]
        validated = False
        last_hop_index = -2
        last_hop = {}
        while not validated:
            last_hop = measurement_data[0]["result"][last_hop_index]
            # Check if there is results
            if "x" in last_hop["result"][0].keys():
                last_hop_index += -1
                continue
            if self.is_IP_anycast(last_hop["result"][0]["from"]):
                last_hop_index += -1
                continue
            if not self.hop_from_directions_are_equal(last_hop):
                last_hop_index += -1
                continue
            validated = True
        return last_hop

    def obtain_pings_near_last_hop(self, last_hop_geo):
        print("###########")
        print("Pings phase initiated")
        print("###########")
        # Make pings from probes around last_hop_geo
        probes_id_list = self.find_probes_in_circle(
            latitude=last_hop_geo["latitude"],
            longitude=last_hop_geo["longitude"],
            radius=self._radius,
            num_probes=7
        )
        pings_data = {
            "definitions": [
                {
                    "target": self._target,
                    "description": "Hunter pings %s" % self._target,
                    "type": "ping",
                    "is_oneoff": True,
                    "af": 4,
                    "packets": 3
                }
            ],
            "probes": [
                {
                    "requested": len(probes_id_list),
                    "type": "probes",
                    "value": ",".join(map(str, probes_id_list))
                }
            ]
        }
        self.make_ripe_measurement(data=pings_data)
        if self._measurement_id == 0:
            print("Measure could not start")
            return
        else:
            print("Measure ID: ", self._measurement_id)
        # Obtain results
        self._results_measurements["pings"] = \
            self.get_measurement_results()

    def check_ping_discs_intersection(self) -> bool:
        # Build discs
        self._ping_discs = []
        for ping_result in self._results_measurements["pings"]:
            ping_radius = ((ping_result["min"]/2)*0.001) * \
                          (FIBER_RI*SPEED_OF_LIGHT)
            probe_location = self.get_probe_coordinates(ping_result["prb_id"])
            self._ping_discs.append({
                "probe_id": ping_result["prb_id"],
                "latitude": probe_location["latitude"],
                "longitude": probe_location["longitude"],
                "rtt_min": ping_result["min"],
                "radius": ping_radius
            })

        # Check all disc intersection
        for disc1 in self._ping_discs:
            for disc2 in self._ping_discs:
                if disc1 == disc2:
                    continue
                elif check_discs_intersect(disc1, disc2):
                    continue
                else:
                    return False
        return True

    def check_airports_inside_intersection(self):
        airports_df = pd.read_csv("datasets/airports.csv", sep="\t")
        airports_df.drop(["pop",
                          "heuristic",
                          "1", "2", "3"], axis=1, inplace=True)

        def check_inside_intersection(airport_code) -> bool:
            airport_to_check = airports_df[
                (airports_df["#IATA"] == airport_code)
            ]
            lat_long_string = airport_to_check["lat long"].values[0]
            (airport_lat, airport_lon) = lat_long_string.split(" ")
            a = {"latitude": float(airport_lat),
                 "longitude": float(airport_lon)}
            for disc in self._ping_discs:
                b = {"latitude": disc["latitude"],
                     "longitude": disc["longitude"]}
                if distance(a=a, b=b) < disc["radius"]:
                    continue
                else:
                    return False
            return True

        airports_df["inside_intersection"] = airports_df["#IATA"].apply(
            lambda airport_code: check_inside_intersection(airport_code)
        )

        airports_inside_df = airports_df[(
                airports_df["inside_intersection"] == True
        )].copy()

        cities_results = list(airports_inside_df["city"].unique())
        airports_inside_df.drop(["inside_intersection"], axis=1, inplace=True)
        airports_inside_df.rename(columns={"#IATA": "IATA_code"}, inplace=True)
        airports_located = airports_inside_df.to_dict("records")
        for airport_located in airports_located:
            (lat, lon) = airport_located["lat long"].split(" ")
            airport_located["latitude"] = float(lat)
            airport_located["longitude"] = float(lon)
            airport_located.pop("lat long", None)

        self._results_measurements["hunt_results"] = {
            "cities": cities_results,
            "airports_located": airports_located
        }

    def save_measurements(self):
        self._results_measurements["target"] = self._target
        dict_to_json_file(self._results_measurements,
                          self._measurement_result_filepath)

# Not class exclusive functions

    def find_probes_in_circle(self,
                              latitude: float, longitude: float,
                              radius: float, num_probes: int) -> list:
        filters = "radius={},{}:{}".format(latitude, longitude, radius)
        fields = "fields=id,geometry,status"
        url = "{}?{}&{}".format(RIPE_ATLAS_PROBES_BASE_URL, filters, fields)
        probes_inside = requests.get(url=url).json()
        print("Probes inside area ", len(probes_inside["results"]))
        probes_connected = list(filter(
            lambda probe: probe["status"]["name"] == "Connected",
            probes_inside["results"]))
        print("Probes connected inside area (circle of {} km radius): {}".
              format(self._radius, len(probes_connected)))
        if len(probes_connected) == 0:
            print("No probes in a {} km circle.".format(radius))
            return self.find_probes_in_circle(
                latitude=latitude,
                longitude=longitude,
                radius=radius+10,
                num_probes=num_probes
            )
        elif len(probes_connected) < num_probes:
            print("Less than {} probes suitable in area".format(num_probes))
            num_probes = len(probes_connected)
        probes_selected = random.sample(probes_connected, num_probes)
        ids_selected = [probe["id"] for probe in probes_selected]
        print("IDs probes selected: ", ids_selected)
        return ids_selected

    def get_ripe_key(self) -> str:
        return json_file_to_dict(KEY_FILEPATH)["key"]

    def is_IP_anycast(self, ip: str) -> bool:
        return False

    def hop_from_directions_are_equal(self, hop: dict) -> bool:
        initial_direction = hop["result"][0]["from"]
        for result in hop["result"]:
            if initial_direction != result["from"]:
                return False
        return True

    def geolocate_ip_commercial_database(self, ip: str) -> dict:
        latlng = geocoder.ip(ip).latlng
        return {
            "latitude": latlng[0],
            "longitude": latlng[1]
        }

    def get_probe_coordinates(self, probe_id: int) -> dict:
        url = RIPE_ATLAS_PROBES_BASE_URL + "/%s" % probe_id
        probe_response = requests.get(url).json()

        latitude = probe_response["geometry"]["coordinates"][1]
        longitude = probe_response["geometry"]["coordinates"][0]
        return {
            "latitude": latitude,
            "longitude": longitude
        }

    # def make_box_centered_on_origin(self) -> Polygon:
    #     return box(xmin=self._origin[0] - self._separation,
    #                ymin=self._origin[1] - self._separation,
    #                xmax=self._origin[0] + self._separation,
    #                ymax=self._origin[1] + self._separation)
