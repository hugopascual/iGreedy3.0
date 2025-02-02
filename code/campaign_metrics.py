#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external modules imports
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# internal modules imports
from utils.constants import (
    GROUND_TRUTH_VALIDATIONS_CAMPAIGNS_PATH,
    METRICS_CSV_PATH
)
from utils.common_functions import (
    json_file_to_dict,
    dict_to_json_file,
    get_list_files_in_path
)


def plot_campaign_statistics_comparison(validations_df: pd.DataFrame,
                                        campaign_name: str,
                                        parameter: str):
    parameter_unique_values = validations_df[parameter].unique()
    parameter_unique_values.sort()
    probes_filename_unique_values = validations_df["probes_filename"].unique()

    colors = ["magenta", "red", "green", "blue", "goldenrod"]
    colors_assigned = {}
    for probe_filename in probes_filename_unique_values:
        colors_assigned[probe_filename] = colors[
            list(probes_filename_unique_values).index(probe_filename)]

    figure = make_subplots(rows=2,
                           cols=2,
                           subplot_titles=["Accuracy",
                                           "Precision",
                                           "Recall",
                                           "F1"])
    # Add accuracy subplot
    for probes_filename in probes_filename_unique_values:
        figure.add_trace(go.Scatter(
            x=parameter_unique_values,
            y=validations_df.loc[
                validations_df["probes_filename"] == probes_filename]
            ["accuracy"],
            name=probes_filename,
            line_color=colors_assigned[probes_filename],
            legendgroup=probes_filename
        ), row=1, col=1)
    # Add precision subplot
    for probes_filename in probes_filename_unique_values:
        figure.add_trace(go.Scatter(
            x=parameter_unique_values,
            y=validations_df.loc[
                validations_df["probes_filename"] == probes_filename]
            ["precision"],
            name=probes_filename,
            line_color=colors_assigned[probes_filename],
            legendgroup=probes_filename,
            showlegend=False
        ), row=1, col=2)
    # Add recall subplot
    for probes_filename in probes_filename_unique_values:
        figure.add_trace(go.Scatter(
            x=parameter_unique_values,
            y=validations_df.loc[
                validations_df["probes_filename"] == probes_filename]
            ["recall"],
            name=probes_filename,
            line_color=colors_assigned[probes_filename],
            legendgroup=probes_filename,
            showlegend=False
        ), row=2, col=1)
    # Add F1 subplot
    for probes_filename in probes_filename_unique_values:
        figure.add_trace(go.Scatter(
            x=parameter_unique_values,
            y=validations_df.loc[
                validations_df["probes_filename"] == probes_filename]
            ["f1"],
            name=probes_filename,
            line_color=colors_assigned[probes_filename],
            legendgroup=probes_filename,
            showlegend=False
        ), row=2, col=2)
    figure.update_layout(title_text="{}_{}".format(campaign_name, parameter))
    figure.show()


def compare_campaign_statistics(campaign_name: str,
                                parameter: str,
                                specification=""):
    if specification != "":
        campaign_filepath = GROUND_TRUTH_VALIDATIONS_CAMPAIGNS_PATH + \
                            "{}_{}_{}/".format(campaign_name,
                                               parameter,
                                               specification)
    else:
        campaign_filepath = GROUND_TRUTH_VALIDATIONS_CAMPAIGNS_PATH + \
                            "{}_{}/".format(campaign_name, parameter)
    try:
        validations_list = get_list_files_in_path(campaign_filepath)
    except Exception as e:
        print(e)
        return

    validations_df = pd.DataFrame(columns=[
        "target", "probes_filename",
        "alpha", "threshold", "noise",
        "accuracy", "precision", "recall", "f1",
        "TP", "FP", "TN", "FN"
    ])
    for validation_file in validations_list:
        data = json_file_to_dict(campaign_filepath + validation_file)
        validations_df = pd.concat(
            [pd.DataFrame([[
                data["target"],
                data["probes_filepath"].split("/")[-1][:-5],
                data["alpha"],
                data["threshold"],
                data["noise"],
                data["statistics"]["accuracy"],
                data["statistics"]["precision"],
                data["statistics"]["recall"],
                data["statistics"]["f1"],
                data["statistics"]["TP"],
                data["statistics"]["FP"],
                data["statistics"]["TN"],
                data["statistics"]["FN"]
            ]], columns=validations_df.columns),
                validations_df],
            ignore_index=True)
    validations_df.sort_values(by=["probes_filename", parameter], inplace=True)
    if specification != "":
        validations_df.to_csv(
            "datasets/ploted_metrics_csv/{}_{}_{}.csv".format(
                campaign_name, parameter, specification),
            sep='\t',
            encoding='utf-8')
    else:
        validations_df.to_csv(
            "datasets/ploted_metrics_csv/{}_{}.csv".format(
                campaign_name, parameter),
            sep='\t',
            encoding='utf-8')

    #plot_campaign_statistics_comparison(validations_df,
    #                                    campaign_name,
    #                                    parameter)


def do_campaign():
    root_campaign_name = "North-Central_20230410"
    root_servers_ip_directions = [
        "198.41.0.4",
        "199.9.14.201",
        "192.33.4.12",
        "199.7.91.13",
        "192.203.230.10",
        "192.5.5.241",
        "192.112.36.4",
        "198.97.190.53",
        "192.36.148.17",
        "192.58.128.30",
        "193.0.14.129",
        "199.7.83.42",
        "202.12.27.33"]
    cloudfare_campaign_name = "North-Central_20230418"
    cloudfare_servers_ip_directions = [
        "104.16.123.96"
    ]

    light_factor = "light-factor_0.18"
    '''
    campaign_name_prefix = root_campaign_name
    servers_ip_directions = root_servers_ip_directions
    for ip in servers_ip_directions:
        campaign_name_complete = "{}_{}".format(ip, campaign_name_prefix)
        compare_campaign_statistics(campaign_name_complete,
                                    "alpha",
                                    light_factor)
        compare_campaign_statistics(campaign_name_complete,
                                    "threshold",
                                    light_factor)

    campaign_name_prefix = cloudfare_campaign_name
    servers_ip_directions = cloudfare_servers_ip_directions
    for ip in servers_ip_directions:
        campaign_name_complete = "{}_{}".format(ip, campaign_name_prefix)
        compare_campaign_statistics(campaign_name_complete,
                                    "alpha",
                                    light_factor)
        compare_campaign_statistics(campaign_name_complete,
                                    "threshold",
                                    light_factor)

    campaign_name_prefix = "Europe-countries_20230413"
    servers_ip_directions = cloudfare_servers_ip_directions
    for ip in servers_ip_directions:
        campaign_name_complete = "{}_{}".format(ip, campaign_name_prefix)
        compare_campaign_statistics(campaign_name_complete,
                                    "alpha",
                                    light_factor)
        compare_campaign_statistics(campaign_name_complete,
                                    "threshold",
                                    light_factor)
                                    
    campaign_name_prefix = "North-Central-section_20230425"
    servers_ip_directions = root_servers_ip_directions
    for ip in servers_ip_directions:
        campaign_name_complete = "{}_{}".format(ip, campaign_name_prefix)
        compare_campaign_statistics(campaign_name_complete,
                                    "alpha",
                                    light_factor)
        compare_campaign_statistics(campaign_name_complete,
                                    "threshold",
                                    light_factor)
    '''
    campaign_name_prefix = "North-Central-section_20230426"
    servers_ip_directions = cloudfare_servers_ip_directions
    for ip in servers_ip_directions:
        campaign_name_complete = "{}_{}".format(ip, campaign_name_prefix)
        compare_campaign_statistics(campaign_name_complete,
                                    "alpha",
                                    light_factor)
        compare_campaign_statistics(campaign_name_complete,
                                    "threshold",
                                    light_factor)


def plot_target_statistics_comparison(target: str, parameter: str):
    files = get_list_files_in_path(METRICS_CSV_PATH)
    files.sort()

    for metrics_csv_file in files:
        if (target in metrics_csv_file) and (parameter in metrics_csv_file):
            validations_df = pd.read_csv(METRICS_CSV_PATH+metrics_csv_file,
                                         sep="\t")
            plot_campaign_statistics_comparison(
                validations_df=validations_df,
                campaign_name=metrics_csv_file,
                parameter=parameter
            )
        else:
            continue
###############################################################################


ip_directions = [
    "198.41.0.4",
    "199.9.14.201",
    "192.33.4.12",
    "199.7.91.13",
    "192.203.230.10",
    "192.5.5.241",
    "192.112.36.4",
    "198.97.190.53",
    "192.36.148.17",
    "192.58.128.30",
    "193.0.14.129",
    "199.7.83.42",
    "202.12.27.33",
    "104.16.123.96"]
plot_target_statistics_comparison(target="104.16.123.96", parameter="alpha")
#do_campaign()
