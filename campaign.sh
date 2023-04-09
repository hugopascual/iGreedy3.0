#!/bin/bash

num_probes_array=(100 300 500 1000)
alpha_array=(0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1)
#areas_array=("North-Central" "North-East" "South-Central" "South-East" "West" "WW")
#areas_array=("North-Central" "WW")
areas_array=("North-Central")

root_servers_ip_directions=(
"198.41.0.4" "199.9.14.201" "192.33.4.12" "199.7.91.13" "192.203.230.10"
"192.5.5.241" "192.112.36.4" "198.97.190.53" "192.36.148.17" "192.58.128.30"
"193.0.14.129" "199.7.83.42" "202.12.27.33")
root_server_ip_direction_selected="192.5.5.241"
root_servers_names=(
"A" "B" "C" "D" "E" "F" "G" "H" "I" "J" "K" "L" "M"
)

probes_filenames_array=()
probes_filepaths_array=()

campaign_name="20230408"

fill_probes_arrays()
{
  for area in "${areas_array[@]}"; do
    for num_probes in "${num_probes_array[@]}"; do
      probes_filenames_array+=($area"_"$num_probes)
      probes_filepaths_array+=("datasets/probes_sets/"$area"_"$num_probes.json)
    done
  done
}

measurement_campaign_ip_selected()
{
  campaign_log_file="Campaign_"$1"_$(date +%F_%T).txt"
  for probes_filepath in "${probes_filepaths_array[@]}"; do
    echo ./igreedy.sh -m "$1" \
    -p "$probes_filepath" \
    | tee -a "campaigns_logs/$campaign_log_file"

    #Start the measurements and save the results in a txt file
    ./igreedy.sh -m "$1" \
    -p "$probes_filepath" \
    | tee -a "campaigns_logs/$campaign_log_file"

    echo "########################################" >> "campaigns_logs/$campaign_log_file"
  done
}

alpha_iterations_results()
{
  campaign_measurements_directory=$1
  groundtruth_comparison_file=$2

  for measurement in "$campaign_measurements_directory"/*; do
    for alpha in "${alpha_array[@]}"; do
      ./igreedy.sh -i "$measurement" \
      -a "$alpha" \
      -g "$groundtruth_comparison_file"
    done
  done
}

fill_probes_arrays
for index in "${!root_servers_ip_directions[@]}"; do
  # Make measurements with all probes files to an ip
  ip="${root_servers_ip_directions[$index]}"
  #measurement_campaign_ip_selected "$ip"

  # Generate results with alpha iterations
  root_server_filename="root_servers_${root_servers_names[$index]}"
  alpha_iterations_results "datasets/measurements/" \
  "datasets/ground-truth/root_servers/$root_server_filename"
done

