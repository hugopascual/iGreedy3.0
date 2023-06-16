#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external modules imports
import pandas as pd
from shapely import Point
from shapely import from_geojson
# internal modules imports
from utils.constants import (
    HUNTER_MEASUREMENTS_CAMPAIGNS_PATH,
    HUNTER_MEASUREMENTS_CAMPAIGNS_STATISTICS_PATH,
    GROUND_TRUTH_VALIDATIONS_CAMPAIGNS_PATH,
    GT_VALIDATIONS_STATISTICS,
    DISTANCE_FUNCTION_USED
)
from utils.common_functions import (
    get_list_files_in_path,
    json_file_to_dict,
    get_nearest_airport_to_point,
    dict_to_json_file,
    get_list_folders_in_path
)


class HunterStatistics:

    def __init__(self,
                 validation_campaign_directory: str = None,
                 output_filename: str = None,
                 validate_target: bool = True):
        self._validation_campaign_directory = validation_campaign_directory
        self._output_filename = output_filename
        self._validate_target = validate_target

    def hunter_build_statistics_validation_campaign(self):
        if (not self._validation_campaign_directory) or (
                not self._output_filename):
            print("No campaign name or output filename provided")
            return

        results_filenames = get_list_files_in_path(
            HUNTER_MEASUREMENTS_CAMPAIGNS_PATH +
            self._validation_campaign_directory)
        validation_results_df = pd.DataFrame(columns=[
            "filename",  "num_countries", "num_cities",
            "num_airports", "country_outcome", "country_outcome_reason",
            "city_outcome", "city_outcome_reason", "from_host", "target"
        ])

        results_not_gt = []

        for result_filename in results_filenames:
            print(result_filename)
            result_dict = json_file_to_dict("{}/{}".format(
                HUNTER_MEASUREMENTS_CAMPAIGNS_PATH +
                self._validation_campaign_directory, result_filename)
            )

            if not result_dict["gt_info"]:
                results_not_gt.append(result_filename)
                continue

            outcome_country = self.calculate_hunter_result_outcome(
                result_dict, "country")
            outcome_city = self.calculate_hunter_result_outcome(
                result_dict, "city")

            validation_results_df = pd.concat(
                [pd.DataFrame([[
                    result_filename,
                    len(result_dict["hunt_results"]["countries"]),
                    len(result_dict["hunt_results"]["cities"]),
                    len(result_dict["hunt_results"]["airports_located"]),
                    outcome_country[0],
                    outcome_country[1],
                    outcome_city[0],
                    outcome_city[1],
                    result_dict["target"],
                    result_dict["traceroute_from_host"],
                ]], columns=validation_results_df.columns,
                ), validation_results_df],
                ignore_index=True
            )

        validation_results_df.sort_values(
            by=["country_outcome", "country_outcome_reason", "filename"],
            inplace=True)
        validation_results_df.to_csv(
            HUNTER_MEASUREMENTS_CAMPAIGNS_STATISTICS_PATH + "statistics_" +
            self._output_filename + ".csv",
            sep=",",
            index=False
        )

        dict_to_json_file(
            results_not_gt,
            HUNTER_MEASUREMENTS_CAMPAIGNS_STATISTICS_PATH +
            "results_not_valid/results_not_gt_" +
            self._output_filename + ".json")

    def calculate_hunter_result_outcome(self, results: dict, param: str) -> \
            (str, str):
        if param == "city":
            result_param = "cities"
            gt_param = "city"
        elif param == "country":
            result_param = "countries"
            gt_param = "country_code"
        else:
            print("Outcome param not valid")
            return "Indeterminate", "Not calculated"

        print("Param: {} Result_param: {} GT_param: {}".format(
            param, result_param, gt_param
        ))

        if self._validate_target:
            try:
                if len(results["hops_directions_list"][-1]) != 1:
                    return "Indeterminate", "Multiples IP on target hop"
                elif results["hops_directions_list"][-1] == "*":
                    return "Indeterminate", "Target hop do not respond"
            except:
                print("Target directions list exception")

        num_result_countries = len(results["hunt_results"]["countries"])
        if num_result_countries == 1:
            if results["gt_info"][gt_param] == \
                    results["hunt_results"][result_param][0]:
                return "Positive", "Same result airport"
            else:
                return "Negative", "Different result airport"
        elif num_result_countries == 0:
            centroid = from_geojson(results["hunt_results"]["centroid"])
            if not results["last_hop"]["ip"]:
                return "Indeterminate", "Last hop not valid"
            elif not results["last_hop"]["geolocation"]:
                return "Indeterminate", "Last hop not geolocated"
            elif not results["discs_intersect"]:
                return "Indeterminate", "Ping discs no intersection"
            elif not centroid:
                return "Indeterminate", "Centroid not found"
            else:
                nearest_airport = get_nearest_airport_to_point(centroid)
                if results["gt_info"][gt_param] == \
                        nearest_airport[gt_param]:
                    return "Positive", "Same result in nearest airport"
                else:
                    return "Negative", "Different result in nearest airport"
        else:
            return "Indeterminate", "Too many results"

    def aggregate_hunter_statistics_country(self):
        statistics_files = [filename for filename in
                            get_list_files_in_path(
                                HUNTER_MEASUREMENTS_CAMPAIGNS_STATISTICS_PATH)
                            if "statistics" in filename]
        aggregation_df = pd.DataFrame(columns=[
            "validation",
            "country_positives", "country_negatives", "country_indeterminates",
            "moment_of_campaign", "filename"
        ])
        for statistic_file in statistics_files:
            statistic_df = pd.read_csv(
                HUNTER_MEASUREMENTS_CAMPAIGNS_STATISTICS_PATH + statistic_file)

            campaign_moment_split_list = statistic_file.split("_")[-2:]
            campaign_hour = campaign_moment_split_list[1].split(".")[0]
            campaign_date = "{}_{}".format(
                campaign_moment_split_list[0],
                campaign_hour
            )

            country_positives = len(
                statistic_df[statistic_df['country_outcome'] == "Positive"])
            country_negatives = len(
                statistic_df[statistic_df['country_outcome'] == "Negative"])
            country_indeterminates = len(
                statistic_df[statistic_df['country_outcome'] ==
                             "Indeterminate"])

            if "ip_target_validation" in statistic_file:
                validation_name = "ip_target_validation"
            elif "ip_all_validation" in statistic_file:
                validation_name = "ip_all_validation"
            elif "no_ip_validation" in statistic_file:
                validation_name = "no_ip_validation"
            elif "ip_last_hop_validation" in statistic_file:
                validation_name = "ip_last_hop_validation"
            else:
                validation_name = ""

            aggregation_df = pd.concat(
                [pd.DataFrame([[
                    validation_name,
                    country_positives,
                    country_negatives,
                    country_indeterminates,
                    campaign_date,
                    statistic_file
                ]], columns=aggregation_df.columns,
                ), aggregation_df],
                ignore_index=True
            )

        aggregation_df.sort_values(by=[
            "moment_of_campaign", "validation"],
            inplace=True)
        aggregation_df.to_csv(
            HUNTER_MEASUREMENTS_CAMPAIGNS_STATISTICS_PATH +
            "aggregation_results.csv",
            sep=",",
            index=False
        )


def get_statistics_hunter():
    hunter_campaigns_folders = get_list_folders_in_path(
        HUNTER_MEASUREMENTS_CAMPAIGNS_PATH)

    hunter_campaigns = [folder for folder in hunter_campaigns_folders
                        if not ("statistics" in folder)]

    for hunter_campaign in hunter_campaigns:
        for validate_target in [True, False]:
            additional_to_name = False
            if hunter_campaign.split("_")[5] == "ip":
                additional_to_name = True
            campaign_name = "_".join(
                map(str, hunter_campaign.split("_")[:5]))
            time = "_".join(
                map(str, hunter_campaign.split("_")[-2:]))
            if validate_target:
                if not additional_to_name:
                    validation_name = "ip_target_validation"
                else:
                    validation_name = "ip_all_validation"
            else:
                if not additional_to_name:
                    validation_name = "no_ip_validation"
                else:
                    validation_name = "ip_last_hop_validation"

            output_filename = "{}_{}_{}".format(campaign_name,
                                                validation_name,
                                                time)
            hunter_campaign_statistics = HunterStatistics(
                validation_campaign_directory=hunter_campaign,
                output_filename=output_filename,
                validate_target=validate_target
            )
            hunter_campaign_statistics.\
                hunter_build_statistics_validation_campaign()


get_statistics_hunter()
statistics = HunterStatistics()
statistics.aggregate_hunter_statistics_country()

